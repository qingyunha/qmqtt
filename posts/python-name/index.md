+++
date = "2016-08-22T22:23:25+08:00"
title = "python值传递 or 引用传递"
categories = ["blog",]
+++

当被问到python是值传递还是引用传递的时候，你要回答都不是。

要理解这个问题，首先要知道Python中变量，赋值是怎么一回事，它和C语言有很大不同。
在C语言中，变量可以想象成一个只能装特定类型值的盒子，`int a = 5`，把数字5放到`a`盒子中。`int b = a`，则把`a`中的5复制一份放入`b`盒子中。而在Python中，通常的赋值过程被称作[__name binding__](https://docs.python.org/3/reference/executionmodel.html)，这还包括类和函数定义，import语句，当然还有函数的形参。Python中一切都是对象，即使是数字5，那么现在`a = 5`的意思就是为5这个对象绑定了一个名字`a`。你可以把变量想象成一个标签，它现在贴在5这个对象上。`b = a`, 就是为5又打了个新标签`b`。

现在就可以很容易解释下面这两个列子：
```python
a = 1
def fun(a):
    a = 2
fun(a)
print(a)  # 1
```

```python
l = []
def fun(l):
    l.append(1)
fun(l)
print(l)  # [1]
```
有人把这种现象归因于可变对象和不可变对象的区别，而其实这两者并没有可比性，如果把第二个例子改一下：
```python
l = []
def fun(l):
    l = [1, 2, 3]
fun(l)
print(l)  # []
```
列表是可变的啊，为什么最后没有打印`[1, 2, 3]`？在`fun`开始执行时形参`l`和`fun`外的`l`（不同的作用域）都贴在`[]`上，当`l = [1, 2, 3]`被执行，只是把形参`l`从`[]`上撕下贴到了`[1, 2, 3]`上，而`fun`外的`l`却依然贴在`[]`上。

那么Python的参数传递方式到底该叫什么呢？`call-by-object-reference`，`call-by-assignment`？在CPython的实现中，名字也是一个对象，而所有的对象都通过`PyObject *`来引用，名字和对象的绑定关系就是保存在一个Python的字典结构中。不管是赋值还是参数传递，都只是改变了作用域字典中名字对应的对象的引用。也许`call-by-object-reference`更好些。

## reference

[how-do-i-pass-a-variable-by-reference](http://stackoverflow.com/questions/986006/how-do-i-pass-a-variable-by-reference)

[Is Python pass-by-reference or pass-by-value?](http://robertheaton.com/2014/02/09/pythons-pass-by-object-reference-as-explained-by-philip-k-dick/)


