+++
date = "2016-08-18T20:21:26+08:00"
title = "memcached-1.2.0 源码解读"
categories = ["blog",]
tags = [
    "memcached",
]

+++

*关键词* ： libevent，状态机，内存分配，hash表

---

memcached是一个免费开源的高性能分布式(由客户端提供)对象缓存系统。这篇将对memcached 1.2.0的源码的进行一点解读，这是我能找到的最早的发行版。协议定义在`doc/protocol.txt`下，代码量在3500行左右：
```bash
$ wc *.[ch]
   186    844   5912 assoc.c
    71    328   1963 config.h
    70    370   2649 daemon.c
   322   1056   8560 items.c
  2282   7820  68519 memcached.c
   278   1379   9781 memcached.h
   356   1392  10717 slabs.c
  3565  13189 108101 total
```
编译需要安装libevent依赖和autotools工具。

## libevent
libevent提供了一种当文件描述符的事件(读，写)发生时执行回调函数的机制，也支持信号和超时回调。memcached用的是libevent的1.x版本，使用了这样几个API：

- `struct event_base *event_init(void)`
- `void event_set(struct event *, int, short, void(*)(int, short, void *), void *)`
- `int event_add(struct event *ev, const struct timeval *timeout)`
- `int event_del(struct event *)`
- `int event_loop(int)`

memcached的`main`函数首先调用`event_init`，这是使用libevent的必须步骤。接着`main`函数创建监听socket，并为其描述符的读事件设置回调函数。另外还添加了两个周期性事件：更新当前时间，一秒一次；删除items，5秒一次。最后`event_loop`被调用，事件循环正式开始。 随着连接的建立、协议的通讯，事件通过`event_add`和`event_del`动态的添加和删除。

## 状态转化
memcached将一次链接的所有信息都封装在结构体`struct conn`中，包括socket的文件描述符，事件，当前状态，输入输出缓存，items等。部分结构如下

```C
typedef struct {
    int    sfd;
    int    state;
    struct event event;
 
    char   *rbuf;   /* buffer to read commands into */

    char   *wbuf;

    char   *ritem;  /* when we read in an item's value, it goes here */
   

    void   *item;     /* for commands set/add/replace  */
    int    item_comm; /* which one is it: set/add/replace */

   
    /* data for the mwrite state */
    struct iovec *iov;
    int    iovsize;   /* number of elements allocated in iov[] */
} conn;
```

conn结构中的state记录这个连接的当前状态，一共定义了7个状态。

```C
enum conn_states {
    conn_listening,  /* the socket which listens for connections */
    conn_read,       /* reading in a command line */
    conn_write,      /* writing out a simple response */
    conn_nread,      /* reading in a fixed number of bytes */
    conn_swallow,    /* swallowing unnecessary bytes w/o storing */
    conn_closing,    /* closing this connection */
    conn_mwrite      /* writing out many items sequentially */
};
```

其中`conn_listening`只属于监听socket，不会改变。当新连接建立时，分配一个conn结构并初始化为`conn_read`状态。

* `set|add|replace <key> <flags> <exptime> <bytes>\r\n`

这一类命令分为2部分，`text line`和`unstructured data`
当memcached接收完`text line`后，`conn_read`-->`conn_nread`，等待读取n个字节长的`unstructured data`，n由`text line`中的bytes指定。读完之后，`conn_nread`-->`conn_write`，向客户端发送一行回复信息。最后conn再次变为`conn_read`等待命令输入。

* `get <key>*\r\n`

get命令只有一个`text line`，后面可以有多个key。当memcached读完这条命令后，`conn_read`-->`conn_mwrite`，返回多个items。

## hashtable
memcached的hashtable是大小为`2**20`的`item *`的数组。至于hash函数的算法就略过了，它共定义了3个API：

- `item *assoc_find(char *key)`
- `int assoc_insert(char *key, item *it)`
- `void assoc_delete(char *key)`

顾名思义。

## 内存分配
_Not Implement_

## I/O
memcached支持TCP，UDP，UNIX socket，读直接使用read(2)，写使用sendmsg(2)，并且`struct iovec`是动态分配，保存在`conn`结构中。

