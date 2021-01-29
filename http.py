buffer = bytearray(512)
bmview = memoryview(buffer)


def sendfile(conn, filename):
    """ Send a file to a connection in chunks - lowering memory usage.

    :param socket conn: connection to send the file to
    :param str filename: file the send
    """
    with open(filename, "rb") as fp:
        while True:
            n = fp.readinto(buffer)
            if n == 0:
                break
            conn.write(bmview[:n])
