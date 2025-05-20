# java-project-structure-freemind
一个将Java项目中的所有类进行梳理并生成文件的python脚本.
生成的文件为.mm格式(本质为xml),可以使用开源软件freemind打开,软件可以从[这里](https://freemind.sourceforge.io/wiki/index.php/Download)下载.
### 使用方法
请确保有python环境
```
python main.py 项目路径 [生成文件名称,默认为项目路径名]
```
### 说明
本人对Java语法没有深入了解,这个脚本应该有bug,以后也许会尝试修错.
这是我在读一个Java库时编写为理清结构编写的,泛用性不强,具体如下:
1. 默认每个文件只有一个public类.
2. 无法处理不在方法中的执行语句(应该可以这么称呼?),只适合梳理库文件.
