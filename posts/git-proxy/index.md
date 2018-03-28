+++
date = "2016-08-06T14:38:12+08:00"
title = "git proxy"
categories = ["wiki"]
tags = ["git", "proxy"]

+++

Git支持多种传输协议，ssh、git、HTTP(S)，甚至ftp，rsync。

当使用不同传输方式时，设置代理的方式也不同。

## SSH

当使用SSH协议时，git实际上直接使用ssh命令，所以我们只要给ssh设置好代理就可以了。在~/.ssh/config中：

```
Host github.com
    User                    git
    ProxyCommand            nc -x localhost:1080 %h %p
```

参见ssh_config(5)manual

## HTTP(S)

git使用`libcurl`来处理HTTP和HTTPS，可以通过设置git的`http.proxy`选项：

`git config --global http.proxy socks5://localhost:1080`

也可以直接设置curl支持的环境变量，比如`ALL_PROXY=socks5://localhost:1080`

参见curl(1)的--proxy选项和git-config(1)中的http.proxy

## Git

当使用git传输协议时，你可以设置git的`gitproxy`选项：

`git config --global core.gitproxy git-proxy`

这里的git-proxy是任何一个可执行文件，同时它要能接受2个参数，host、port（git服务器的地址和端口）。git-proxy完成代理工作。

例如这样一个shell脚本：

```shell
#!/usr/bin/env bash

nc -x localhost:1080 $1 $2
```

也可以直接设置环境变量`GIT_PROXY_COMMAND=git-porxy`

参见git_config(1)


## 如何判断git使用何种协议

根据git服务器的url就可以看出：

- ssh://[user@]host.xz[:port]/path/to/repo.git/
- git://host.xz[:port]/path/to/repo.git/
- http[s]://host.xz[:port]/path/to/repo.git/
- ftp[s]://host.xz[:port]/path/to/repo.git/
- rsync://host.xz/path/to/repo.git/

对于SSH协议，还有一种类似scp的语法：

- [user@]host.xz:path/to/repo.git/

参见git-fetch(1)的GIT URLS

## nc命令
nc(netcat)可以用 -X 指定代理方式：socks4、 sockes5、 HTTPS CONNECT，默认为socks5。 -x 指定代理地址。

参见nc(1)

## example
golang的`go get`命令会用到git，你可以这样：


`env ALL_PROXY=socks5://localhost:1080 GIT_PROXY_COMMAND=git-porxy go get -v ./...`

## reference
[Tutorial: how to use git through a proxy](http://cms-sw.github.io/tutorial-proxy.html)
