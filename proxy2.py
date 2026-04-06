#!/usr/bin/env python3

import sys
import http.client
import socket
import select
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from urllib.parse import urlsplit

# Aumentamos o buffer para 32KB. Isso reduz a quantidade de vezes que o 
# processador precisa fazer "System Calls" (syscalls) para ler/escrever dados.
BUFFER_SIZE = 32768 

class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    address_family = socket.AF_INET
    daemon_threads = True

class OptimizedHTTPProxy(BaseHTTPRequestHandler):
    # Timeouts reduzidos de 300s para 60s. 
    # Isso evita que threads fiquem ociosas consumindo RAM no servidor.
    timeout = 60
    upstream_timeout = 60

    def address_string(self):
        # IMPORTANTE: Desativa a resolução reversa de DNS.
        # Por padrão, o Python tenta descobrir o "nome" de cada IP que conecta,
        # o que gera muita latência e uso de CPU/Rede.
        return self.client_address[0]

    def log_message(self, format, *args):
        # Desativamos a escrita de logs para cada requisição.
        # Escrever no disco (I/O) é uma das operações mais lentas do sistema.
        pass

    def do_CONNECT(self):
        address = self.path.split(':')
        host = address[0]
        port = int(address[1]) if len(address) > 1 else 443

        try:
            upstream_sock = socket.create_connection((host, port), timeout=self.timeout)
        except Exception:
            self.send_error(502)
            return

        self.send_response(200, 'Connection Established')
        self.end_headers()

        conns = [self.connection, upstream_sock]
        keep_connection = True
        
        while keep_connection:
            rlist, _, xlist = select.select(conns, [], conns, self.timeout)
            if xlist:
                break
            for r in rlist:
                other = conns[1] if r is conns[0] else conns[0]
                try:
                    # Usa o novo tamanho de buffer (32KB)
                    data = r.recv(BUFFER_SIZE)
                    if data:
                        other.sendall(data)
                    else:
                        keep_connection = False
                except:
                    keep_connection = False
                    break
        upstream_sock.close()

    def do_GET(self): self.do_SPAM()
    def do_POST(self): self.do_SPAM()
    def do_HEAD(self): self.do_SPAM()

    def do_SPAM(self):
        content_length = int(self.headers.get('Content-Length', 0))
        # Lê o corpo da requisição do cliente
        req_body = self.rfile.read(content_length) if content_length > 0 else None

        self._clean_headers(self.headers)

        u = urlsplit(self.path)
        netloc = u.netloc or self.headers.get('Host')
        scheme = u.scheme or 'http'
        
        if not netloc:
            self.send_error(400)
            return

        path = f"{u.path}?{u.query}" if u.query else u.path
        if not path: path = "/"

        conn = http.client.HTTPConnection(netloc, timeout=self.upstream_timeout) if scheme == 'http' \
               else http.client.HTTPSConnection(netloc, timeout=self.upstream_timeout)
        
        try:
            conn.request(self.command, path, req_body, self.headers)
            res = conn.getresponse()
            
            self.send_response(res.status, res.reason)
            for k, v in res.getheaders():
                if k.lower() not in ['connection', 'transfer-encoding']:
                    self.send_header(k, v)
            self.end_headers()

            if self.command != 'HEAD':
                # STREAMING: Esta é a maior economia de RAM do script.
                # Em vez de carregar a resposta inteira na memória (ex: um vídeo de 500MB),
                # ele repassa de 32KB em 32KB direto para o cliente.
                while True:
                    chunk = res.read(BUFFER_SIZE)
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    
        except Exception:
            self.send_error(502)
        finally:
            conn.close()

    def _clean_headers(self, headers):
        hop_headers = ['connection', 'keep-alive', 'proxy-authenticate', 
                       'proxy-authorization', 'te', 'trailers', 'transfer-encoding', 'upgrade']
        for h in hop_headers:
            if h in headers:
                del headers[h]

def run_server(port=8080):
    # Aumenta a fila de espera do Socket para evitar conexões recusadas em picos
    ThreadingHTTPServer.request_queue_size = 128
    httpd = ThreadingHTTPServer(('', port), OptimizedHTTPProxy)
    
    print(f"Proxy de Alta Performance rodando na porta {port}...")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nDesligando...")
        httpd.server_close()

if __name__ == '__main__':
    p = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    run_server(p)
