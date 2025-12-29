"""Process command runner for executing shell commands with output capture."""

import select
import subprocess
import time


class ProcessCommand:
    """Run a subprocess command with non-blocking output capture."""

    def __init__(self, command_arg_list):
        """Initialize ProcessCommand.

        Args:
            command_arg_list: List of command arguments (e.g., ['ls', '-la'])
        """
        self.proc = None
        self.output = None
        self.command_arg_list = command_arg_list

    def get_command_line(self):
        """Get the command as a string."""
        return " ".join(self.command_arg_list)

    def start(self):
        """Start the subprocess.

        Returns:
            The subprocess.Popen instance
        """
        self.proc = subprocess.Popen(
            self.command_arg_list,
            stdout=subprocess.PIPE,
            stdin=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=0,
        )
        return self.proc

    def poll(self):
        """Poll for new output and check if process has finished.

        Returns:
            Tuple of (return_code, new_output_bytes).
            return_code is None if still running.
        """
        new_output = b""
        if not self.proc:
            return None, new_output
        new_output = self._read_all_so_far()
        if self.proc.returncode is not None:
            new_output += self.proc.stdout.read()
        return self.proc.returncode, new_output

    def send(self, data):
        """Send data to the process stdin.

        Args:
            data: Bytes to send
        """
        self.proc.stdin.write(data)

    def is_alive(self):
        """Check if the process is still running."""
        return self.proc and self.proc.poll() is None

    def _read_all_so_far(self):
        """Read all available output without blocking."""
        output = b""
        while self.proc.poll() is None and (select.select([self.proc.stdout], [], [], 0)[0] != []):
            output += self.proc.stdout.read(1)
        return output

    def run_process(self, output_console=None):
        """Run the process synchronously.

        Args:
            output_console: Optional Qt text widget for output display
        """
        gen = self.run_process_async(output_console)
        while True:
            try:
                gen.__next__()
                time.sleep(0.01)
            except StopIteration:
                return

    def run_process_async(self, output_console=None):
        """Run the process as a generator for async operation.

        Args:
            output_console: Optional Qt text widget for output display

        Yields:
            None on each poll iteration
        """
        if output_console:
            output_console.appendHtml(
                "<b>Command:</b><br/>" + self.get_command_line() + "<br/><br/><b>Output:</b><br/><br/>"
            )
        else:
            print("Command:\n{}\n\nOutput:\n".format(self.get_command_line()), flush=True)
        self.start()
        while True:
            ret, output = self.poll()
            if output:
                if output_console:
                    output_console.appendPlainText(output.decode())
                else:
                    print(output.decode(), end="", flush=True)
            if ret is not None:
                break
            yield
        if output_console:
            output_console.appendHtml("<br/><b>Return Code:</b> {}".format(ret) + "<br/><br/><br/>")
        else:
            print("\nReturn Code: {}\n".format(ret), flush=True)
