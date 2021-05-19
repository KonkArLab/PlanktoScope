from loguru import logger

import time

import socketserver
import http.server
import threading
import multiprocessing

# assert_new_image = threading.Condition()

# object_stream = multiprocessing.Queue()
receiver, sender = multiprocessing.Pipe()


################################################################################
# Classes for streaming
################################################################################
class StreamingHandler(http.server.BaseHTTPRequestHandler):
    def __init__(self, delay, *args, **kwargs):
        self.delay = delay
        super(StreamingHandler, self).__init__(*args, **kwargs)

    @logger.catch
    def do_GET(self):
        global receiver
        if self.path == "/":
            self.send_response(301)
            self.send_header("Location", "/object.mjpg")
            self.end_headers()
        elif self.path == "/object.mjpg":
            self.send_response(200)
            self.send_header("Age", 0)
            self.send_header("Cache-Control", "no-cache, private")
            self.send_header("Pragma", "no-cache")
            self.send_header(
                "Content-Type", "multipart/x-mixed-replace; boundary=FRAME"
            )

            self.end_headers()
            try:
                while True:
                    if receiver.poll():
                        logger.debug("Got a new object in the pipe!")
                        try:
                            file = receiver.recv()
                        except EOFError as e:
                            logger.error(
                                "Pipe has been closed, nothing is left here, let's die"
                            )
                            break
                        frame = file.getvalue()
                        self.wfile.write(b"--FRAME\r\n")
                        self.send_header("Content-Type", "image/jpeg")
                        self.send_header("Content-Length", len(frame))
                        self.end_headers()
                        self.wfile.write(frame)
                        self.wfile.write(b"\r\n")
                        time.sleep(self.delay)
                    else:
                        time.sleep(0.2)

            except BrokenPipeError as e:
                logger.info(f"Removed streaming client {self.client_address}")
        else:
            self.send_error(404)
            self.end_headers()


class StreamingServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    allow_reuse_address = True
    daemon_threads = True
