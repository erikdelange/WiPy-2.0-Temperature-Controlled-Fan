# Routines for decoding an HTTP request line.
#
# HTTP request line as understood by this package:
#
#   Request line: Method SP Request-URL SP HTTP-Version CRLF
#   Request URL: Path ? Query
#   Query: key=value&key=value
#
# Example: b"GET /page?key1=0.07&key2=0.03&key3=0.13 HTTP/1.1\r\n"
#
#   Method: GET
#   Request URL: /page?key1=0.07&key2=0.03&key3=0.13
#   HTTP version: HTTP/1.1
#   Path: /page
#   Query: key1=0.07&key2=0.03&key3=0.13
#
# See also: https://www.tutorialspoint.com/http/http_requests.htm
#           https://en.wikipedia.org/wiki/Uniform_Resource_Identifier
#
# Intended use: memory constrained MicroPython server applications which
# must communicate with a browser based user interface via Javascript
# fetch() or XMLHttpRequest() API calls. Not a replacement for library's
# like Requests.


def query(request):
    """ Place all key-value pairs from a request URL's query string into a dict.

    Example: request b"GET /page?key1=0.07&key2=0.03&key3=0.13 HTTP/1.1\r\n"
    yields dictionary {'key1': '0.07', 'key2': '0.03', 'key3': '0.13'}.

    :param str request: the complete HTTP request line.
    :return dict: dictionary with zero of more entries.
    """
    d = dict()
    p = request.find(b"?")  # only look in the query part of a request URL
    if p != -1:
        p_space = request.find(b" ", p)
        while True:
            n_start = p + 1
            n_end = request.find(b"=", n_start)
            v_start = n_end + 1
            p_and = request.find(b"&", v_start)
            v_end = p_space if p_and == -1 else min(p_space, p_and)
            key = request[n_start:n_end].decode("utf-8")
            if key not in d:
                d[key] = request[v_start:v_end].decode("utf-8")
            p = v_end
            p = request.find(b"&", p)
            if p == -1:
                break
    return d


def value(request, key):
    """ Return the value for a single key-value pair from a request URL's query string.

    The query string may contain multiple key-value pairs. If key occurs
    multiple times in the query string the first value is extracted.

    :param str request: the complete HTTP request line.
    :param str key: the key to search in the query string.
    :return value: None if key is not present in the URL's query string.
    """
    value = None
    query = request.find(b"?")  # only look in the query string of a request-URL
    if query != -1:
        n_start = request.find(key.encode("utf-8"), query)
        if n_start != -1:
            v_start = request.find(b"=", n_start) + 1
            v_space = request.find(b" ", v_start)
            v_and = request.find(b"&", v_start)
            v_end = v_space if v_and == -1 else min(v_space, v_and)
            value = request[v_start:v_end].decode("utf-8")
    return value


def path(request):
    """ Extract the URL path from a HTTP request line.

    Convention: the URL for an absolute path is never empty, at least a
    forward slash is present.

    :param str request: the complete HTTP request line.
    :return str path: path (without the query string)
    """
    u_start = request.find(b"/")
    p_space = request.find(b" ", u_start)
    p_query = request.find(b"?", u_start)
    u_end = p_space if p_query == -1 else min(p_space, p_query)
    return request[u_start:u_end].decode("utf-8")


def request(line):
    """ Separate an HTTP request line in its elements and put them into a dict.

    :param str line: the complete HTTP request line.
    :return dict: dictionary containing
            method      the request method ("GET", "PUT", ...)
            url         the request URL, including the query string (if any)
            path        the request path from the URL
            query       the query string from the URL (if any, else "")
            version     the HTTP version
            parameters  dictionary with key-value pairs from the query string
            header      placeholder for key-value pairs from request header fields
    """
    d = {key: value for key, value in zip(["method", "url", "version"], line.decode("utf-8").split())}

    d["parameters"] = query(line)

    question = d["url"].find("?")

    d["path"] = d["url"] if question == -1 else d["url"][0:question]
    d["query"] = "" if question == -1 else d["url"][question + 1:]
    d["header"] = dict()

    return d


##if __name__ == "__main__":
##
##    request_lines = [ b"GET / HTTP/1.1\r\n",
##                      b"GET /page/sub HTTP/1.1\r\n",
##                      b"GET /page?key1=0.07&key1=0.03 HTTP/1.1\r\n",
##                      b"GET /page?key1=0.07&key2=0.03 HTTP/1.1\r\n" ]
##
##    for line in request_lines:
##        print(line)
##        print("value  :", "key1 =", value(line, "key1"))
##        print("query  :", query(line))
##        print("path   :", path(line))
##        print("request:", request(line))
##        print()
