import subprocess
import select
import time


class ProcessCommand:
    def __init__(self, command_arg_list):
        self.proc = None
        self.output = None
        self.command_arg_list = command_arg_list

    def get_command_line(self):
        return ' '.join(self.command_arg_list)

    def start(self):
        self.proc = subprocess.Popen(self.command_arg_list,
            stdout=subprocess.PIPE,
            stdin=subprocess.PIPE,
            stderr=subprocess.STDOUT)
        return self.proc

    def poll(self):
        new_output = b''
        if not self.proc:
            return None, new_output
        new_output = self._read_all_so_far()
        if self.proc.returncode is not None:
            new_output += self.proc.stdout.read()
        return self.proc.returncode, new_output

    def send(self, data):
        self.proc.stdin.write(data)

    def is_alive(self):
        return self.proc and self.proc.poll() is None

    def _read_all_so_far(self):
        output = b''
        while self.proc.poll() is None and (select.select([self.proc.stdout],[],[],0)[0] != []):
            output += self.proc.stdout.read(1)
        return output

    def run_process(self, output_console=None):
        gen = self.run_process_async(output_console)
        while True:
            try:
                gen.__next__()
                time.sleep(0.01)
            except StopIteration:
                return

    def run_process_async(self, output_console=None):
        if output_console:
            output_console.appendHtml('<b>Command:</b><br/>' + self.get_command_line() + '<br/><br/><b>Output:</b><br/><br/>')
        self.start()
        while True:
            ret, output = self.poll()
            if output:
                if output_console:
                    output_console.appendPlainText(output.decode())
            if ret is not None:
                break
            yield
        if output_console:
            output_console.appendHtml('<br/><b>Return Code:</b> {}'.format(ret) + '<br/><br/><br/>')
