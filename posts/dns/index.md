+++
date = "2016-09-11T20:23:16+08:00"
title = "理解DNS"

+++

## 简介

域名系统（Domain Name System），它最常用的功能就是把域名解析成IP。什么是域名（domain name），计算机在网络中的名字。它能让我们通过名字来找到网络中的机器，而不能去记住那些无意义的IP地址。可以把它想象成一个地址薄，上面记录着域名和IP的对应关系。事实上，在早期确实有这样一个文件HOSTS.TXT，它被网络中的所有主机所共享。但随着网络结构的改变，这种方式变得不可行。现在的域名系统是一个分布式的数据库，与之对应的，域名本身也是分层的。

## 域名结构

域名是一个树形结构。从下到上以`.`连接，如`A.ISI.EDU`
```
                                   |
                                   |
             +---------------------+------------------+
             |                     |                  |
            MIL                   EDU                ARPA
             |                     |                  |
             |                     |                  |
       +-----+-----+               |     +------+-----+-----+
       |     |     |               |     |      |           |
      BRL  NOSC  DARPA             |  IN-ADDR  SRI-NIC     ACC
                                   |
       +--------+------------------+---------------+--------+
       |        |                  |               |        |
      UCI      MIT                 |              UDEL     YALE 
                |                 ISI
                |                  |
            +---+---+              |
            |       |              |
           LCS  ACHILLES  +--+-----+-----+--------+
            |             |  |     |     |        |
            XX            A  C   VAXA  VENERA Mockapetris

```


## 记录（Resouce Record）

实现上一个域名可以对应多个信息，而IP地址只是其中的一个。这样一个信息被称为这个域名的一个记录或者RR，记录是分类型，比如IP地址是一个A类记录。其他记录类型有AAAA（IPv6地址）、MX（邮件服务地址）、NS（域名服务器）等。DNS被设计为可扩展的，记录类型是可以增加的，因此一个域名理论上可以被解析为任意的消息。

* A
* SOA
* NS
* PTR

## 逆向解析


## Zone Transfer

一个域名服务器负责整个域名空间的一部分，就像上图中树中的一棵子树。这样的部分空间叫做`Zone`。每个Zone维护着一个像HOSTS.TXT的文件，上面记录着该空间的所有域名信息。如：

```
co.kp.          432000  IN  SOA ns1.co.kp. root.co.kp. 2013082900 28800 86400 1209600 86400
co.kp.          432000  IN  NS  ns1.co.kp.
co.kp.          432000  IN  NS  ns2.co.kp.
ns1.co.kp.      432000  IN  A   175.45.176.15
ns2.co.kp.      432000  IN  A   175.45.176.16
star.co.kp.     432000  IN  NS  ns1.star.co.kp.
star.co.kp.     432000  IN  NS  ns2.star.co.kp.
ns1.star.co.kp.     432000  IN  A   175.45.176.15
ns2.star.co.kp.     432000  IN  A   175.45.176.16
co.kp.          432000  IN  SOA ns1.co.kp. root.co.kp. 2013082900 28800 86400 1209600 86400
```

一个Zone可以有多个域名服务器，以防止单点故障。其中有一台是主服务器，域名信息的改变最先是在主服务器上的，这就需要一个方法来同步所有服务器。DNS使用Zone transfer，与其他DNS消息不同，Zone transfer可以使用TCP，以保证域名信息传输的可靠性，完整性。处于安全考虑，域名服务器可以关闭Zone trnasfer，或者增加一些限制，如只允许指定IP地址的服务器使用Zone transfer。（最近朝鲜顶级域名服务器的错误配置，允许Zone transfer，DNS数据泄露[https://github.com/mandatoryprogrammer/NorthKoreaDNSLeak]）


## DNS实现（组成，报文结构，通讯协议）


## 现实中的DNS（注册域名， 搭建DNS服务器）
