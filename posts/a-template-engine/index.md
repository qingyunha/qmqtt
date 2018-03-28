+++
date = "2015-10-09T11:32:25+08:00"
title = "A Template Engine"
categories = ["translation"]
tags = [
    "python",
    "template engine",
]

+++
## Introduction

大多数程序包含大量的逻辑和点点文本数据，编程语言被设计成适合做这样的 事情。但是有些编程任务只需要点点逻辑和大量的文本数据，对于这样的任务， 我们希望有一个更合适工具来做。模板引擎就是这样一个工具。在这一章，我 们会开发一个简单的模板引擎。

一个最常见的需要处理多文本数据的例子是web应用。web应用的一个重要部分 是为浏览器生成HTML网页。很少网页是完全静态的，它们至少包含一些动态数 据，比如用户名。一般情况下，网页有很大一部分动态数据：产品列表，好友消息更 新等等。

同时，每个HTML网页包含大量的静态文本。并且这些网页很大，有成千上万个 字节。这时，web开发者就有一个问题要解决：怎样才能最有效的生成同时包 含静态和动态数据的长字符串？随之而来的问题，这些静态文本其实是前端工 程师写的HTML，他们想希望用自己熟悉的方法处理这些HTML。

为了说明，让我们假设想生成这样一个简单的HTML
```html
<p>Welcome, Charlie!</p>
<p>Products:</p>
<ul>
    <li>Apple: $1.00</li>
    <li>Fig: $1.50</li>
    <li>Pomegranate: $3.25</li>
</ul>
```
这里，用户名会是动态的，产品的名称和数量也是动态的，甚至产品的数量也 不是固定的：在其他情况，可能有更多或更少的产品。

一个简单的方法生成这样的网页是把这样的字符串作为常量写入我们的代码中， 然后把它们拼在一起完成这个网页。动态数据使用类似字符替换的方法插入进 去。有些动态数据是重复的，比如产品列表，这就是说我们会有一些重复的 HTML段，所以我们要单独的去处理它们再和其他的HTML合并起来。

使用这种方法生成我们的HTML的代码会像这样
```python
# The main HTML for the whole page.
PAGE_HTML = """
<p>Welcome, {name}!</p>
<p>Products:</p>
<ul>
{products}
</ul>
"""

# The HTML for each product displayed.
PRODUCT_HTML = "<li>{prodname}: {price}</li>\n"

def make_page(username, products):
    product_html = ""
    for prodname, price in products:
        product_html += PRODUCT_HTML.format(prodname=prodname, price=format_price(price))
    html = PAGE_HTML.format(name=username, products=product_html)
    return html
```
这样可以，但是我们搞得乱七八糟，HTML成了我们代码里的字符串常量，我们 很难看出这个HTML的结构，因为它被分成一段一段的了。数据格式的细节迷失 在python代码中。并且，为了修改HTML，我们的前端工程师需要修改python代 码。想象一下，如果这个网页比现在这个复杂10倍（或者100倍）我们代码会 是什么样子。

## Templates

更好的方法是用模板来生成HTML，或者说把HTML写成一个模板，这样绝大部分 就是静态HTML，再加上一点使用特别符号的动态内容。现在我们的toy网页就成了 下面这样的模板
```html
<p>Welcome, {{user_name}}!</p>
<p>Products:</p>
<ul>
{% for product in product_list %}
    <li>{{ product.name }}:
        {{ product.price|format_price }}</li>
{% endfor %}
</ul>
```
这里我们关注的是HTML文本，另外加上一点逻辑。对比现在以文本为中心的方 法和之前以逻辑为中心的方法，我们之前的程序大部分是python代码，这里我 的程序大部分是静态的HTML标签。

在模板中采用的以静态为主的风格和大多数编程语言的工作方式相反。比如 python，几乎所有的源文件都是可执行代码，如果你需要静态文本，你就要把 它嵌到字符串中。
```python
def hello():
    print("Hello world!")

hello()
```
当python读取这个源文件时，它把`def hello():`这样的文本解释成要被执行 的指令，而在双引号中的字符 `print("Hello, world!")`被指示成文本。这 就是编程语言如何工作的：动态的，嵌入点点静态内容。静态的内容通过双引号来指示。

一个模板语言把这个过程反过来了，大部分是静态文本，用特殊的符号指示动态 内容。

`<p>Welcome, {{user_name}}!</p>`

这里的文本会直接出现在最终的HTML中，直到遇到 `{{` 符号，它指示转换到 动态模式，这里`user_name`变量就会被替换。

字符串格式化函数，比如python的 `"foo = {foo}!".format(foo=17)`就是一 个在字符串并插入数据创建文本的微型语言的例子。模板更进一步，加上逻辑结构，比如条件，循环。这只是在程度上不同。

把这些文件叫做模板是因为它们被用来生成大量结构相似的网页，只是细节不同。

为了在程序中使用HTML模板，我们需要一个模板引擎(template engine)：一个需要两个参数的函数，一个是描述页面结构和内容的静态模板，另一个是包含要插入到模板中的动态数据的上下文。模板引擎把模板和上下文结合起来生成完整的HTML字符串，它的任务是解释模板，用真正的数据替换动态的部分。

顺便说一下，HTML对模板引擎并没有什么特别的地方，它可以用来生成任何文本数据。比如，它可以被用来生成纯文本的email信息。但是它通常用于HTML，或许碰巧还有些专门对HTML的特性，比如转义，这个特性让你不用担心插入了对HTML有特殊含义的字符。

## Supported Syntax

不同的模板引擎在语法支持上各有不同。我们的模板语法基于Django，一个非常流行的网站框架。因为我们的引擎使用python实现的，一些python的概念会出现在我们的语法中。在上一节的HTML中我们已经看到了一些语法，这里是我们语法的小总结。

上下文中的数据插入到两个大括号中

`<p>Welcome, {{user_name}}!</p>`

在模板中可用的数据在上下文中，后面我们详细的讲到。

我们的模板引擎提供了一个简单自由的语法访问数据中的元素。在python中，这些表达式有不同的效果：
```python
dict["key"]
obj.attr
obj.method()
```
在我们的语法中，所有这些操作都用点号表示。
```
dict.key
obj.attr
obj.method
```
这个点号会访问对象的属性，字典里的值，如果结果是可调用的，那么就自动调用它。这与python代码不同，你需要不同的语法完成不同的操作。在我们简单的语法下会是这样：

`<p>The price is: {{product.price}}, with a {{product.discount}}% discount.</p>`

点号可以在一个值上多次使用以访问元素链。

你还可以使用帮助函数，把它们叫做过滤器，用管道符号调用

`<p>Short name: {{story.subject|slugify|lower}}</p>`

制作有趣的网页通常需要一点逻辑，所以我们有条件表达式：
```html
{% if user.is_logged_in %}
    <p>Welcome, {{ user.name }}!</p>
{% else %}
    <p><a href="/login">Log in </a></p>
{% endif %}
```
循环可以让我们在网页里包含数据集合：
```
<p>Products:</p>
<ul>
{% for product in product_list %}
    <li>{{ product.name }}: {{ product.price|format_price }}</li>
{% endfor %}
</ul>
```
和其他的编程语言一样，条件和循环可以嵌套使用。

最后，我们可以对模板注释

`{# This is the best template ever! #}`

## Implementation Approaches

粗略的说，模板引擎有两个主要的部分，解析和呈现。

对于模板的呈现包括下面这几个部分： 
- 管理动态上下文，它是数据的来源 
- 执行逻辑元素
- 执行数据访问和过滤器

解析模板后应该传递什么给下一步是个关键问题。解析模板输出什么？这里有两个选择：我们称它们为`解释`(interpretation) 和`编译`(complilation), 这是借用其他语言实现的术语。

使用解释模式，解析产出一个代表模板结构的数据结构，呈现部分会一步一步的处理这个数据结构，组合它发现的文本数据。作为一个真实的例子，Django的模板引擎就是使用这种方法。

编译模式，解析后直接产出某种形式的可执行代码，呈现部分就会执行这个代码产出结果。Jinja2和Mako是使用编译方法的模板引擎的例子。

我们的模板引擎使用编译的方式实现。我们把模板编译成python代码，执行它，产生结果。

这里描述的模板引擎起源于covery.py的一部分，它用来生成HTML报告，在coverage.py中只有几个模板，它们被频繁的使用，总之，如果模板被编译成python代码的话程序会更快，即使编译过程有点复杂。编译一次，运行多次。这会比解释一个数据结构快很多倍。

编译过程有点复杂，但不是你想象的那么难。并且可能有开发者告诉你一个自己能写程序的程序会更有趣些。

我们的模板编译器是一个通用技术的小例子，叫做代码生成器。代码生成是很多强大灵活的工具的基础，包括语言编译器。代码生成器可能非常复杂，但是它会是你工具箱里的一个有用的工具。

## Compiling to Python
