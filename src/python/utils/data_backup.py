from subprocess import run
import os
import datetime

try:
    import mount_drive
    import hd_test
    import rsync
except:
    try:
        import utils.mount_drive as mount_drive
        import utils.hd_test as hd_test
        import utils.rsync as rsync
    except:
        import src.python.utils.mount_drive as mount_drive
        import src.python.utils.hd_test as hd_test
        import src.python.utils.rsync as rsync

def driveExists(drivesMounted, partition, mountpoint) -> bool:
    drive = drivesMounted.get(partition[:3])
    if drive != None:
        parts = drive.get('parts')
        # If there are partitions
        if parts != None:
            part = parts.get(partition)
            # If the partition is found
            if part != None:
                if part.get('mountpoint') == mountpoint:
                    print(partition + ' mounted!')
                    return True
                else:
                    if hd_test.isSudo():
                        run(['mount', '/dev/' + partition, mountpoint])
                        return True
                    else:
                        print('Mounting requires sudo privileges!')

    return False

def calcFreeSpace(mountpoint):
    result = run(['df', mountpoint], capture_output=True)
    df = result.stdout.decode('utf-8').splitlines()[1].split()
    return int(df[3])


def calcFolderSize(mountpoint):
    result = run(['df', mountpoint], capture_output=True)
    df = result.stdout.decode('utf-8').splitlines()[1].split()
    return int(df[2])


def scanUsers(drivetype, mountpoint) -> list:
    userList = []
    if drivetype == 'apfs':
        usersDir = mountpoint + '/root/Users'
        dirs = os.listdir(usersDir)
        for dir in dirs:
            if dir[0] != '.' and dir != 'Guest' and dir != 'Shared' and os.path.isdir(usersDir + '/' + dir) and not os.path.islink(usersDir + '/' + dir):
                userList.append(dir)
    else:
        usersDir = mountpoint + '/Users'
        dirs = os.listdir(usersDir)
        for dir in dirs:
            if dir[0] != '.' and dir != 'Default' and dir != 'Public' and os.path.isdir(usersDir + '/' + dir) and not os.path.islink(usersDir + '/' + dir):
                userList.append(dir)
    return userList


def backupData(customer_name, ticket_number, mountpoint, drivetype, users:list) -> str:
    # TODO: Make those reconfigurable via GUI
    BACKUP_SERVER_PART_1 = 'sda2'
    BACKUP_SERVER_PART_2 = 'sdb2'
    BACKUP_SERVER_MOUNT_1 = '/home/techstop/NET_TRANSFER/BACKUP1'
    BACKUP_SERVER_MOUNT_2 = '/home/techstop/NET_TRANSFER/BACKUP2'
    bks1Mounted = False
    bks2Mounted = False
    bks1HasSpace = False
    bks2HasSpace = False
    bks1FreeSpace = 0
    bks2FreeSpace = 0
    
    backupDrive = ''
    drivesMounted = mount_drive.listDrive()

    # If the drive exists
    bks1Mounted = driveExists(drivesMounted, BACKUP_SERVER_PART_1, BACKUP_SERVER_MOUNT_1)
    bks2Mounted = driveExists(drivesMounted, BACKUP_SERVER_PART_2, BACKUP_SERVER_MOUNT_2)

    # Make sure at least one of the two are mounted
    if not (bks1Mounted or bks2Mounted):
        print('No backup servers available. Stopping backup')
        return
    
    # Check if they have enough space
    if bks1Mounted:
        bks1FreeSpace = calcFreeSpace(BACKUP_SERVER_MOUNT_1)
        if bks1FreeSpace >= calcFolderSize(mountpoint):
            bks1HasSpace = True
    if bks2Mounted:
        bks2FreeSpace = calcFreeSpace(BACKUP_SERVER_MOUNT_2)
        if bks2FreeSpace >= calcFolderSize(mountpoint):
            bks2HasSpace = True
    
    # Make sure at least one drive has space
    if not (bks1HasSpace or bks2HasSpace):
        print('No backup servers available. Stopping backup')
        return

    # Select the drive with more free space
    if bks1FreeSpace > bks2FreeSpace:
        backupDrive = BACKUP_SERVER_MOUNT_1
    else:
        backupDrive = BACKUP_SERVER_MOUNT_2
    print('Selected ' + backupDrive)
    
    # Create folder for the backup
    backupDir = customer_name + ' ' + str(ticket_number)
    absBackupDir = backupDrive + '/' + backupDir
    if not os.path.isdir(absBackupDir):
        os.mkdir(absBackupDir)
        print('Created backup folder: ' + absBackupDir)
    
    # Create folder for the backup user and backup
    for user in users:
        timenow = datetime.datetime.now().strftime("-%Y-%m-%d-%H-%M-%S")
        userBackupDir = absBackupDir + '/' + user + timenow
        os.mkdir(userBackupDir)
        if drivetype == 'ntfs' or drivetype == 'BitLocker':
            sourceDir = mountpoint + '/Users/' + user
            rsync.rsync_run_verbose(['AppData', 'Cookies', 'OneDrive', 'Dropbox'], sourceDir, userBackupDir)
        elif drivetype == 'apfs':
            sourceDir = mountpoint + '/root/Users/' + user
            rsync.rsync_run_verbose(['Library'], sourceDir, userBackupDir)
        else:
            print('Something went wrong')
    
    return absBackupDir

# backupData('Lawrence Bisong', '19264660', '/media/techstop/DAC62B66C62B41DD', 'ntfs', ['Lawrence Bisong'])
# users = scanUsers('apfs', '/media/samueljiang/mac')
# print(users)