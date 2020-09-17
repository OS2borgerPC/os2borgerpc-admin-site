from datetime import datetime
# Dont give timestamp as argument
# csv format: TimeStamp, securityEventCode, Tec sum, Raw data

def write_data(data):
    if not data:
        return

    line = datetime.now().strftime('%Y%m%d%H%M')

    for d in data:
        line += ',' + d.replace('\n', ' ').replace('\r', '').replace(',', '')

    with open("/etc/os2borgerpc/security/securityevent.csv", "at") as csvfile:
        csvfile.write(line + "\n")
