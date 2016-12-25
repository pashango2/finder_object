#! usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function, absolute_import

"""
# 汎用検索オブジェクト

QAbstractItemViewに対して付加可能な検索オブジェクト。
ツリー型モデルとテーブル型の両対応をしている。
"""
from PySide.QtCore import *
from PySide.QtGui import *

__version__ = "0.1"


class FinderObject(QObject):
    indexFound = Signal(QModelIndex)

    MAX_HISTORY = 10

    def __init__(self, view, parent=None):
        """
        :type view: QAbstractItemView
        :type parent: QObject or None
        """
        super(FinderObject, self).__init__(parent or view)
        self.model = view.model()
        self.view = view
        self._cmp_func = self._default_cmp
        self._find_str = ""
        self._current_index = QModelIndex()
        self.find_role = Qt.DisplayRole
        self._history = []

        self.indexFound.connect(self.view.setCurrentIndex)

    def _default_cmp(self, find_str, index):
        """ 標準の比較関数
        :type find_str: str or unicode
        :type index: QModelIndex
        """
        data = index.data(self.find_role)
        return data and find_str.lower() in data.lower()

    def setCompareFunction(self, cmp_func):
        """ 比較関数を設定する
        :type cmp_func: (str or unicode, QModelIndex) -> bool
        """
        self._cmp_func = cmp_func

    def next_index(self, index=QModelIndex()):
        """ 次のQModelIndexを求める
        :rtype: QModelIndex
        :type index: QModelIndex
        """
        if index.isValid():
            _index = index.child(0, 0)
            if not _index.isValid():
                _index = index.sibling(index.row(), index.column() + 1)
                if not _index.isValid():
                    _index = index.sibling(index.row() + 1, 0)
                    if not _index.isValid():
                        _index = index.parent()
                        _index = _index.sibling(_index.row() + 1, 0)
                        if not _index.isValid():
                            _index = self.model.index(0, 0)
            return _index
        else:
            return self.model.index(0, 0)

    def _last_index(self, index=QModelIndex()):
        """ 最後の葉のQModelIndexを求める
        :type index: QModelIndex
        """
        while self.model.rowCount(index) > 0:
            index = self.model.index(self.model.rowCount(index) - 1, 0, index)
            index = index.sibling(index.row(), self.model.columnCount(index.parent()) - 1)
        return index

    def prev_index(self, index=QModelIndex()):
        """ 前のQModelIndexを求める
        :rtype: QModelIndex
        :type index: QModelIndex
        """
        if index.isValid():
            _index = index.sibling(index.row(), index.column() - 1)
            if not _index.isValid():
                _index = index.sibling(index.row() - 1, 0)
                if _index.isValid():
                    _index = self._last_index(_index)
                if _index.isValid():
                    _index = _index.sibling(_index.row(), self.model.columnCount(_index.parent()) - 1)
                if not _index.isValid():
                    _index = index.parent()
                    if not _index.isValid():
                        _index = self._last_index()
            return _index
        else:
            return self._last_index()

    @Slot(str)
    def find(self, find_str):
        """ 検索
        :type find_str: str or unicode
        """
        self._find_str = find_str
        current_index = self.view.currentIndex()
        if not current_index.isValid() and self._cmp_func(find_str, current_index):
            self.view.setCurrentIndex(current_index)
            find_flag = True
        else:
            find_flag = self._find()

        if find_flag:
            for i, h in enumerate(self._history):
                if find_str.startswith(h):
                    self._history[i] = find_str
                    self._rollup_history(i)
                    break
                elif h.startswith(find_str):
                    self._rollup_history(i)
                    break
            else:
                self._add_history(find_str)

        return find_flag

    def _find(self, forward=True):
        """ 検索（内部関数）
        :type forward: bool
        """
        if not self._find_str:
            return

        index = self.view.currentIndex()
        index = stop_index = self.next_index(index) if forward else self.prev_index(index)
        while True:
            if self._cmp_func(self._find_str, index):
                self.indexFound.emit(index)
                return True

            index = self.next_index(index) if forward else self.prev_index(index)
            if index == stop_index or not index.isValid():
                break

        return False

    @Slot()
    def findNext(self):
        """ 次を探索 """
        self._find()

    @Slot()
    def findPrevious(self):
        """ 前を探索 """
        self._find(forward=False)

    def createFindNextAction(self, text, parent=None):
        """
        :type parent: QWidget
        :type text: str or unicode
        """
        act = QAction(text, parent, triggered=self.findNext)
        act.setShortcut(QKeySequence.FindNext)
        return act

    def createFindPreviousAction(self, text, parent=None):
        """
        :type parent: QWidget
        :type text: str or unicode
        """
        act = QAction(text, parent, triggered=self.findPrevious)
        act.setShortcut(QKeySequence.FindPrevious)
        return act

    def _add_history(self, word):
        self._history.insert(0, word)
        if len(self._history) > self.MAX_HISTORY:
            self._history.pop()

    def _rollup_history(self, i):
        if i > 0:
            h = self._history[i]
            del self._history[i]
            self._history.insert(0, h)


class PopupFinderObject(FinderObject):
    def __init__(self, view, parent=None):
        super(PopupFinderObject, self).__init__(view, parent)

    def showPopup(self, geometry=None, use_incremental=True):
        frame = QFrame(self.view)
        frame.setWindowFlags(Qt.Popup | Qt.Window)

        layout = QHBoxLayout(frame)
        layout.setContentsMargins(2, 2, 2, 2)
        line = QLineEdit(frame)
        line.setText(self._find_str)
        line.selectAll()
        line.setFrame(False)
        line.setFocus()
        layout.addWidget(line)

        if use_incremental:
            line.textChanged.connect(self.find)
            line.returnPressed.connect(self.findNext)
        else:
            line.returnPressed.connect(lambda: self.find(line.text()))

        next_act = self.createFindNextAction("次へ", frame)
        prev_act = self.createFindPreviousAction("前へ", frame)
        next_act.setShortcutContext(Qt.WidgetWithChildrenShortcut)
        prev_act.setShortcutContext(Qt.WidgetWithChildrenShortcut)
        frame.addActions([next_act, prev_act])
        next_act.setIcon(QApplication.style().standardIcon(QStyle.SP_ArrowDown))
        prev_act.setIcon(QApplication.style().standardIcon(QStyle.SP_ArrowUp))

        close_act = QAction("閉じる", frame)
        close_act.triggered.connect(frame.close)
        close_act.setIcon(QApplication.style().standardIcon(QStyle.SP_TitleBarCloseButton))

        layout.addWidget(self._create_button(prev_act, frame))
        layout.addWidget(self._create_button(next_act, frame))
        layout.addWidget(self._create_button(close_act, frame))

        completer = QCompleter(self._history, frame)
        line.setCompleter(completer)

        frame.setGeometry(geometry or self._default_geometry(frame))
        frame.show()

        # show history
        line.completer().complete()

    @staticmethod
    def _create_button(act, parent):
        _button = QToolButton(parent)
        _button.setAutoRaise(True)
        _button.setDefaultAction(act)
        return _button

    def _default_geometry(self, frame):
        g = self.view.geometry()
        size = frame.sizeHint()

        return QRect(
            g.x() + g.width() - size.width(),
            g.y() - size.height(),
            size.width(),
            size.height()
        )

    def find(self, find_str):
        """
        :type find_str: str or unicode
        """
        find_flag = super(PopupFinderObject, self).find(find_str)
        if find_flag:
            for i, h in enumerate(self._history):
                if find_str.startswith(h):
                    self._history[i] = find_str
                    self._rollup_history(i)
                    break
                elif h.startswith(find_str):
                    self._rollup_history(i)
                    break
            else:
                self._add_history(find_str)

        return find_flag
