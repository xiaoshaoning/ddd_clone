# 行号字体同步和垂直对齐修复总结

## 问题描述
用户报告使用Ctrl+调整字体大小时，行号区域的字体大小没有同步变化，导致行号和对应行不匹配。此外，调整字体大小后，左边行号比对应行的位置略高一点点，需要中心对齐。

## 问题分析
1. **没有字体调整功能**：`source_viewer.py` 和 `line_number_area.py` 中的字体都被硬编码为12号
2. **没有键盘事件处理**：代码库中没有 `keyPressEvent` 处理Ctrl+快捷键
3. **没有字体同步机制**：当源代码查看器的字体改变时，行号区域的字体没有同步更新
4. **垂直对齐问题**：行号绘制时使用了字体高度作为矩形高度，而不是实际文本块的高度，导致行号在矩形顶部而不是垂直居中

## 修复内容

### 1. `ddd_clone/gui/line_number_area.py`

#### 新增方法
- **`set_font()`** (第23-27行)：允许从外部更新行号区域的字体
- **`changeEvent()`** (第101-112行)：处理字体改变事件，自动触发重绘

#### 修改方法
- **`paintEvent()`** (第65-99行)：
  - 显式设置画笔字体：`painter.setFont(self.font())`
  - 使用实际块高度计算垂直对齐：`block_height = int(bottom - top)`
  - 行号垂直居中：`painter.drawText(rect, Qt.AlignRight | Qt.AlignVCenter, number)`
  - 断点标记垂直居中：`marker_y = int(top) + (block_height - marker_size) // 2`

### 2. `ddd_clone/gui/source_viewer.py`

#### 新增方法
- **`change_font_size()`** (第74-108行)：统一管理字体大小调整
  - 支持增加/减少字体大小（最小8号）
  - 同步更新源代码查看器和行号区域的字体
  - 自动重新计算行号区域宽度和几何形状
- **`keyPressEvent()`** (第342-358行)：处理键盘快捷键
  - **Ctrl+** 或 **Ctrl+=**：增加字体大小
  - **Ctrl-**：减少字体大小

## 使用说明

### 调整字体大小
1. **确保源代码查看器获得焦点**：点击源代码显示区域
2. **调整字体大小**：
   - 按 **Ctrl+** 或 **Ctrl+=** 增大字体
   - 按 **Ctrl-** 减小字体
3. **最小字体限制**：字体大小不会小于8号，防止界面混乱

### 预期效果
1. **字体同步**：行号区域的字体大小与源代码查看器完全同步
2. **行号对齐**：行号区域宽度根据新字体自动调整，确保行号与代码行对齐
3. **垂直居中**：行号和断点标记在对应行的垂直中心位置显示
4. **断点标记对齐**：断点标记根据新字体高度重新计算垂直位置

## 技术实现细节

### 字体同步机制
```python
# 创建新字体并更新
new_font = QFont(current_font)
new_font.setPointSize(new_size)
self.setFont(new_font)
self.line_number_area.set_font(new_font)
```

### 行号区域宽度计算
- 字体改变后调用 `update_line_number_area_width(0)` 重新计算宽度
- 使用 `self.fontMetrics().horizontalAdvance('9')` 计算数字宽度
- 根据最大行号位数动态调整宽度

### 垂直对齐计算
```python
# 获取实际文本块高度
block_height = int(bottom - top)

# 行号垂直居中
rect = QRect(0, int(top), self.width() - 5, block_height)
painter.drawText(rect, Qt.AlignRight | Qt.AlignVCenter, number)

# 断点标记垂直居中
marker_y = int(top) + (block_height - marker_size) // 2
```

### 几何形状更新
```python
# 更新行号区域几何形状
cr = self.contentsRect()
self.line_number_area.setGeometry(
    cr.left(), cr.top(),
    self.line_number_area_width(), cr.height()
)
```

## 测试要点
1. **字体同步测试**：调整字体大小，验证行号区域字体同步变化
2. **对齐测试**：检查行号是否与对应行中心对齐
3. **断点标记测试**：验证断点标记在行中心位置
4. **边界测试**：测试最小字体大小（8号）限制
5. **快捷键测试**：验证Ctrl+和Ctrl-快捷键正常工作

## 提交信息
```
fix: 修复行号字体大小同步和垂直对齐问题

- 添加字体大小调整功能，支持Ctrl+和Ctrl-快捷键
- 行号区域字体与源代码查看器字体同步变化
- 修复行号垂直对齐问题，使用实际块高度确保中心对齐
- 修复断点标记垂直对齐问题
```

## 相关文件
1. `ddd_clone/gui/line_number_area.py` - 行号区域显示
2. `ddd_clone/gui/source_viewer.py` - 源代码查看器（包含行号区域宽度计算）

---

*文档创建时间：2026-02-24*
*修复版本：行号字体同步和垂直对齐修复*