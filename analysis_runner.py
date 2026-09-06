import threading
import traceback

class AnalysisRunner:
    def __init__(self, on_complete, on_error):
        self.on_complete = on_complete
        self.on_error = on_error
        self._thread = None
        self._is_running = False

    def start(self, analysis_func, *args, **kwargs):
        if self._is_running:
            return
        self._is_running = True
        def _run():
            try:
                result = analysis_func(*args, **kwargs)
                self._is_running = False
                self.on_complete(result)
            except Exception as e:
                self._is_running = False
                self.on_error(str(e) + "\n" + traceback.format_exc())
        self._thread = threading.Thread(target=_run)
        self._thread.daemon = True
        self._thread.start()

    def is_running(self):
        return self._is_running

    def join(self):
        if self._thread and self._thread.is_alive():
            self._thread.join()