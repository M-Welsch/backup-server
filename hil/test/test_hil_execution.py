from hil_execution import open_terminal, PCU_SERIAL_BAUDRATE, PCU_SERIAL_DEVICE

def test_open_terminal(tmp_path):
    tmp_logfile = tmp_path/"logfile.log"
    p = open_terminal(PCU_SERIAL_DEVICE, PCU_SERIAL_BAUDRATE, tmp_logfile)
    pass
