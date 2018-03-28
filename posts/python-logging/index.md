+++
date = "2016-07-09T21:32:25+08:00"
title = "python logging"
categories = ["blog",]
tags = [
    "python",
    "logging",
]

+++

日志对程序的调试和问题的发现很有帮助。如何设置合适的日志需要需要一些考虑。

以python2.7标准库logging为例。

logging分有多种级别:

- NOTSET
- DEBUG
- INFO
- WARNING
- ERROR
- CRITICAL

一个应用中可以有多个logger对象，比如每个module一个logger。
不同logger对象可以设置不同的级别，只有大于该级别的log事件才会被记录。

log的记录和处理是分开的，你可以把log简单的打印出来，写到文件中，甚至遇到高级别log事件时，直接给你发邮件。这是由`logging.Handler`对象来处理，你可以为一个logger添加多个handler，同时handler也是分级别的，这样你就可以对不同级别的log做出不同的处理了。

每个Logger都有一个唯一的名字，通常用`logging.getLogger(__name__)`，这样得到的logger的名字就是当前模块的名字,这样还有一个好处，logger是分层的，比如`input`logger就是`input.cvs`，`input.xls`logger的上层。这与python的模块命名空间一致，以`.`做分割。

这里的分层还意味着log事件会向上层传递，当然你也可以阻止这个行为，通过设置`Logger.propagate`为False。

logger，handler，formmater(log的格式)的创建，配置可以直接写在代码中，比如：

```python
import logging

# create logger
logger = logging.getLogger('simple_example')
logger.setLevel(logging.DEBUG)

# create console handler and set level to debug
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)

# create formatter
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# add formatter to ch
ch.setFormatter(formatter)

# add ch to logger
logger.addHandler(ch)

# 'application' code
logger.debug('debug message')
```

logging模块也提供了从配置文件设置的方法，使用函数`fileConfig()`：
```python
import logging
import logging.config

logging.config.fileConfig('logging.conf')

# create logger
logger = logging.getLogger('simpleExample')

# 'application' code
logger.debug('debug message')
```
相应的配置文件如下：
```
[loggers]
keys=root,simpleExample

[handlers]
keys=consoleHandler

[formatters]
keys=simpleFormatter

[logger_root]
level=DEBUG
handlers=consoleHandler

[logger_simpleExample]
level=DEBUG
handlers=consoleHandler
qualname=simpleExample
propagate=0

[handler_consoleHandler]
class=StreamHandler
level=DEBUG
formatter=simpleFormatter
args=(sys.stdout,)

[formatter_simpleFormatter]
format=%(asctime)s - %(name)s - %(levelname)s - %(message)s
datefmt=
```
这种方式的好处是把代码与配置分开。logging还提供了第三种方式，`dictConfig()`,它通过python的`dict`对象来配置。这比第二种方式更进一步，你可以用任何一种配置文件格式，再把它转成符合一定规范的`dict`就可以了。

## reference
[Logging HOWTO](https://docs.python.org/2/howto/logging.html)
