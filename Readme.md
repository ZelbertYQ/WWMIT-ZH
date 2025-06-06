# WWMIT-ZH

全名 WWMI-Tools 汉化版 

汉化自 [WWMI-Tools By SpectrumQT](https://github.com/SpectrumQT/WWMI-Tools)

相较于原版WWMIT，我添加了一些额外功能

1. 将模组信息输出为说明文档，每次F10刷新模组时在屏幕左下角出现2s
   * 将在「mod.ini」同级目录下生成「Readme.md」文档
   * Blender中「模组信息」下的非图标内容将被填充至文档
   * 文档内容可以随意修改，但由于调用WWMI中的Core中的Print模块，故不支持中文和其他字符
   * 文档的配置代码在「mod.ini」中，可以自由调节文档的位置，出现时间，出现逻辑等等，详情请参考原作者说明文档，或者等我暑假可能推出的教程
2. 额外的部件索引切换预设
   * 自动配置变量、索引切换和循环代码
   * 该功能基于100版本新增的自定义导出模板
     * 下载发布版中的「CustomIniTemplateVeXX.txt」
     * 勾选使用自定义模板、选择存储类型为外部文件
     * 重定向为「CustomIniTemplateVeXX.txt」
     * 勾选生成说明文档和使用自定义模板
3. 额外声明
    * 本发布版本仅做学习交流，
    * 本人目前没有任何代码基础
    * 所有额外代码均来源网络、其他作者和AI

4. 安装
   * 我成功重定向了自动更新的仓库，现在这个插件会从我的仓库获取最新版本
   * 但是我未能成功将版本号拓展为X.X.X.X
   * 这也就意味着，如果我提前更新，会与SQT的未来版本产生冲突
   * 故自动更新功能暂时只同步大版本
   * 而我可能会上传一些小版本更新，如1.2.1.1或者1.2.1.3
   * 我会尽量保证大版本的稳定性，小版本则是尝试添加额外内容
   * 下载发行版后可以直接安装，不需要解压缩

如果你想要提交代码，或者反馈问题，请加Q群与我联系：992119724 （最后求个Star）

## 提取预览

![提取预览](https://raw.githubusercontent.com/ZelbertYQ/WWMIT-ZH/main/Images/提取预览.png)

## 导入预览

![导入预览](https://raw.githubusercontent.com/ZelbertYQ/WWMIT-ZH/main/Images/导入预览.png)

## 导出预览

![导出预览](https://raw.githubusercontent.com/ZelbertYQ/WWMIT-ZH/main/Images/导出预览.png)

## 工具箱预览

![工具箱预览](https://raw.githubusercontent.com/ZelbertYQ/WWMIT-ZH/main/Images/工具箱预览.png)