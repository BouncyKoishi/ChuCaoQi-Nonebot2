import os
from typing import Optional


class SensitiveFilter:
    END_MARKER = '\x00'

    def __init__(self):
        self._trie = {}
        self._word_count = 0

    def add_word(self, word: str):
        word = word.strip()
        if not word:
            return
        node = self._trie
        for ch in word:
            if ch not in node:
                node[ch] = {}
            node = node[ch]
        if self.END_MARKER not in node:
            node[self.END_MARKER] = True
            self._word_count += 1

    def load_from_file(self, filepath: str):
        if not os.path.exists(filepath):
            print(f'[SensitiveFilter] 词库文件不存在: {filepath}')
            return
        count = 0
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                word = line.strip()
                if word and not word.startswith('#'):
                    self.add_word(word)
                    count += 1
        print(f'[SensitiveFilter] 从 {filepath} 加载了 {count} 个敏感词')

    def contains(self, text: str) -> bool:
        if not text:
            return False
        for i in range(len(text)):
            node = self._trie
            j = i
            while j < len(text) and text[j] in node:
                node = node[text[j]]
                if self.END_MARKER in node:
                    return True
                j += 1
        return False

    def find_first(self, text: str) -> Optional[str]:
        if not text:
            return None
        for i in range(len(text)):
            node = self._trie
            j = i
            while j < len(text) and text[j] in node:
                node = node[text[j]]
                if self.END_MARKER in node:
                    return text[i:j + 1]
                j += 1
        return None

    def find_all(self, text: str) -> list:
        if not text:
            return []
        results = []
        i = 0
        while i < len(text):
            node = self._trie
            j = i
            last_match = None
            while j < len(text) and text[j] in node:
                node = node[text[j]]
                if self.END_MARKER in node:
                    last_match = text[i:j + 1]
                j += 1
            if last_match:
                results.append(last_match)
                i += len(last_match)
            else:
                i += 1
        return results

    def filter(self, text: str, replace_char: str = '*') -> str:
        if not text:
            return text
        result = list(text)
        i = 0
        while i < len(text):
            node = self._trie
            j = i
            last_end = -1
            while j < len(text) and text[j] in node:
                node = node[text[j]]
                if self.END_MARKER in node:
                    last_end = j
                j += 1
            if last_end >= 0:
                for k in range(i, last_end + 1):
                    result[k] = replace_char
                i = last_end + 1
            else:
                i += 1
        return ''.join(result)

    @property
    def word_count(self) -> int:
        return self._word_count


_instance: Optional[SensitiveFilter] = None


def get_sensitive_filter() -> SensitiveFilter:
    global _instance
    if _instance is None:
        _instance = SensitiveFilter()
        try:
            from config import config
            base_path = config.base_path if hasattr(config, 'base_path') else os.path.dirname(os.path.abspath(__file__))
        except Exception:
            base_path = os.path.dirname(os.path.abspath(__file__))
        filepath = os.path.join(base_path, 'config', 'sensitive_words.txt')
        _instance.load_from_file(filepath)
    return _instance


def reload_sensitive_filter() -> SensitiveFilter:
    global _instance
    _instance = SensitiveFilter()
    try:
        from config import config
        base_path = config.base_path if hasattr(config, 'base_path') else os.path.dirname(os.path.abspath(__file__))
    except Exception:
        base_path = os.path.dirname(os.path.abspath(__file__))
    filepath = os.path.join(base_path, 'config', 'sensitive_words.txt')
    _instance.load_from_file(filepath)
    return _instance
