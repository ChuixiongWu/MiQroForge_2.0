"""agents/node_generator/manual_index.py — 软件手册层级索引。

基于 bm25s 的段落级搜索，支持 5 种导航操作：
  list_chapters()        → 章节目录 + 大小 + 摘要
  get_chapter_outline()  → section 标题列表
  search()               → BM25 关键词搜索
  get_section()          → 指定 section 完整内容
  find_command_docs()    → 命令/关键词定位

依赖：bm25s[core]（numpy + PyStemmer）
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any


# ═══════════════════════════════════════════════════════════════════════════
# 数据结构
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class Section:
    """手册中的一个 section。"""
    section_id: str          # 如 "7.26" 或 "page-734"
    title: str               # section 标题
    page: int | None = None  # PDF 页码（如果有）
    line_start: int = 0      # 在文件中的起始行
    line_end: int = 0        # 在文件中的结束行
    content: str = ""        # section 内容


@dataclass
class ChapterInfo:
    """章节元数据。"""
    name: str                # 文件名（如 "geometry_optimization.md"）
    display_name: str        # 人类可读名
    size_kb: float           # 文件大小 KB
    section_count: int       # section 数量
    summary: str = ""        # 首段摘要


# ═══════════════════════════════════════════════════════════════════════════
# Section 解析
# ═══════════════════════════════════════════════════════════════════════════

# 匹配 ## Page N（ORCA/Gaussian PDF 提取的页码标记）
_RE_PAGE = re.compile(r"^##\s+Page\s+(\d+)", re.MULTILINE)

# 匹配 # Heading 或 ## Heading（markdown 标题）
_RE_HEADING = re.compile(r"^(#{1,3})\s+(.+)$", re.MULTILINE)

# 匹配带编号的 section（如 7.26.1 Geometry Optimization）
_RE_SECTION_NUM = re.compile(r"^(\d+(?:\.\d+)*)\s+(.+)$", re.MULTILINE)


def _parse_sections(content: str, filename: str) -> list[Section]:
    """将 markdown 内容分割为 sections。"""
    lines = content.split("\n")
    sections: list[Section] = []

    # 策略：按 ## Page N 分割（PDF 提取的文档用这种格式）
    # 如果没有 Page 标记，则按 # Heading 分割
    page_markers = [(i, int(m.group(1))) for i, m in enumerate(_RE_PAGE.finditer(content))]

    if page_markers:
        # 按 Page 分割
        for idx, (line_idx, page_num) in enumerate(page_markers):
            # 找到下一个 page marker 或文件末尾
            if idx + 1 < len(page_markers):
                end_line = page_markers[idx + 1][0]
            else:
                end_line = len(lines)

            # 提取 page 内容，跳过 ## Page N 行本身
            section_lines = lines[line_idx + 1:end_line]
            section_text = "\n".join(section_lines).strip()

            if not section_text:
                continue

            # 尝试从内容中提取 section 标题
            title = f"Page {page_num}"
            first_heading = _RE_HEADING.search(section_text)
            if first_heading:
                title = first_heading.group(2).strip()
            else:
                # 尝试提取第一行非空文本作为标题
                for sl in section_lines:
                    sl_stripped = sl.strip()
                    if sl_stripped and not sl_stripped.startswith("#"):
                        title = sl_stripped[:80]
                        break

            sections.append(Section(
                section_id=f"page-{page_num}",
                title=title,
                page=page_num,
                line_start=line_idx,
                line_end=end_line,
                content=section_text,
            ))
    else:
        # 按 # Heading 分割
        headings = list(_RE_HEADING.finditer(content))
        for idx, match in enumerate(headings):
            line_idx = content[:match.start()].count("\n")
            if idx + 1 < len(headings):
                end_line = content[:headings[idx + 1].start()].count("\n")
            else:
                end_line = len(lines)

            section_text = "\n".join(lines[line_idx:end_line]).strip()
            title = match.group(2).strip()

            # 尝试提取 section 编号
            section_id = title.lower().replace(" ", "-")[:40]
            num_match = _RE_SECTION_NUM.match(title)
            if num_match:
                section_id = num_match.group(1)

            sections.append(Section(
                section_id=section_id,
                title=title,
                line_start=line_idx,
                line_end=end_line,
                content=section_text,
            ))

    # 如果没有任何分割标记，整个文件作为一个 section
    if not sections:
        sections.append(Section(
            section_id="full",
            title=filename.replace(".md", "").replace("_", " ").title(),
            line_start=0,
            line_end=len(lines),
            content=content.strip(),
        ))

    return sections


def _extract_summary(content: str, max_chars: int = 300) -> str:
    """提取内容的前几行作为摘要。"""
    lines = content.strip().split("\n")
    summary_lines = []
    char_count = 0
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        # 跳过页码标记
        if stripped.startswith("## Page"):
            continue
        summary_lines.append(stripped)
        char_count += len(stripped)
        if char_count >= max_chars or len(summary_lines) >= 3:
            break
    return " ".join(summary_lines)[:max_chars]


# ═══════════════════════════════════════════════════════════════════════════
# ManualIndex
# ═══════════════════════════════════════════════════════════════════════════

class ManualIndex:
    """软件手册的层级索引，基于 bm25s 的段落级搜索。"""

    def __init__(self, manual_dir: str | Path):
        self.manual_dir = Path(manual_dir)
        self._chapters: dict[str, ChapterInfo] = {}
        self._sections: dict[str, list[Section]] = {}  # chapter → sections
        self._corpus: list[str] = []       # 段落文本（用于 BM25）
        self._corpus_meta: list[dict] = [] # 每段的元数据
        self._bm25 = None
        self._bm25_retriever = None
        self._index_dir = self.manual_dir / ".bm25_index"
        self._built = False

    def build(self) -> None:
        """构建索引（如果已缓存则跳过）。"""
        if self._built:
            return

        if not self.manual_dir.exists():
            self._built = True
            return

        # 扫描所有 .md 文件
        md_files = sorted(self.manual_dir.glob("*.md"))
        if not md_files:
            self._built = True
            return

        # 检查缓存
        cache_file = self._index_dir / "meta.json"
        if self._is_cache_valid(cache_file, md_files):
            try:
                self._load_cache()
                self._built = True
                return
            except Exception:
                pass

        # 构建索引
        self._build_from_files(md_files)
        self._save_cache()
        self._built = True

    def _is_cache_valid(self, cache_file: Path, md_files: list[Path]) -> bool:
        """检查缓存是否仍然有效。"""
        if not cache_file.exists():
            return False
        try:
            meta = json.loads(cache_file.read_text("utf-8"))
            cached_mtime = meta.get("mtime", {})
            for f in md_files:
                if str(f.name) not in cached_mtime:
                    return False
                if cached_mtime[str(f.name)] != f.stat().st_mtime:
                    return False
            return True
        except Exception:
            return False

    def _build_from_files(self, md_files: list[Path]) -> None:
        """从文件构建索引。"""
        import bm25s

        self._chapters = {}
        self._sections = {}
        self._corpus = []
        self._corpus_meta = []

        for md_file in md_files:
            try:
                content = md_file.read_text("utf-8")
            except Exception:
                continue

            filename = md_file.name
            display_name = filename.replace(".md", "").replace("_", " ").title()
            size_kb = md_file.stat().st_size / 1024

            sections = _parse_sections(content, filename)
            self._sections[filename] = sections
            self._chapters[filename] = ChapterInfo(
                name=filename,
                display_name=display_name,
                size_kb=round(size_kb, 1),
                section_count=len(sections),
                summary=_extract_summary(content),
            )

            # 为每个 section 创建 BM25 文档
            for section in sections:
                doc_text = f"{section.title}\n{section.content}"
                self._corpus.append(doc_text)
                self._corpus_meta.append({
                    "chapter": filename,
                    "section_id": section.section_id,
                    "title": section.title,
                    "page": section.page,
                })

        # 构建 BM25 索引
        if self._corpus:
            try:
                stemmer = Stemmer.Stemmer("english")
            except Exception:
                stemmer = None

            tokens = bm25s.tokenize(
                self._corpus,
                stopwords="en",
                stemmer=stemmer,
            )
            self._bm25_retriever = bm25s.BM25()
            self._bm25_retriever.index(tokens)

    def _save_cache(self) -> None:
        """保存索引缓存。"""
        try:
            self._index_dir.mkdir(parents=True, exist_ok=True)

            # 保存元数据
            meta = {
                "mtime": {
                    name: (self.manual_dir / name).stat().st_mtime
                    for name in self._chapters
                    if (self.manual_dir / name).exists()
                },
                "chapters": {k: asdict(v) for k, v in self._chapters.items()},
            }
            (self._index_dir / "meta.json").write_text(
                json.dumps(meta, ensure_ascii=False, indent=2), "utf-8"
            )

            # 保存 BM25 索引
            if self._bm25_retriever:
                self._bm25_retriever.save(str(self._index_dir / "bm25"))

            # 保存 sections（内容太大，只保存元数据）
            sections_meta = {}
            for chapter, secs in self._sections.items():
                sections_meta[chapter] = [
                    {"section_id": s.section_id, "title": s.title, "page": s.page,
                     "line_start": s.line_start, "line_end": s.line_end}
                    for s in secs
                ]
            (self._index_dir / "sections.json").write_text(
                json.dumps(sections_meta, ensure_ascii=False, indent=2), "utf-8"
            )
        except Exception:
            pass

    def _load_cache(self) -> None:
        """从缓存加载索引。"""
        import bm25s

        meta = json.loads((self._index_dir / "meta.json").read_text("utf-8"))
        self._chapters = {
            k: ChapterInfo(**v) for k, v in meta["chapters"].items()
        }

        # 加载 sections 元数据 + 从原文件重建内容
        sections_meta = json.loads(
            (self._index_dir / "sections.json").read_text("utf-8")
        )
        self._sections = {}
        self._corpus = []
        self._corpus_meta = []

        for chapter, secs_meta in sections_meta.items():
            filepath = self.manual_dir / chapter
            if not filepath.exists():
                continue
            content = filepath.read_text("utf-8")
            lines = content.split("\n")

            secs = []
            for sm in secs_meta:
                section_lines = lines[sm["line_start"]:sm["line_end"]]
                section_content = "\n".join(section_lines).strip()
                sec = Section(
                    section_id=sm["section_id"],
                    title=sm["title"],
                    page=sm.get("page"),
                    line_start=sm["line_start"],
                    line_end=sm["line_end"],
                    content=section_content,
                )
                secs.append(sec)
                self._corpus.append(f"{sec.title}\n{sec.content}")
                self._corpus_meta.append({
                    "chapter": chapter,
                    "section_id": sec.section_id,
                    "title": sec.title,
                    "page": sec.page,
                })
            self._sections[chapter] = secs

        # 加载 BM25 索引
        bm25_path = self._index_dir / "bm25"
        if bm25_path.exists() and self._corpus:
            self._bm25_retriever = bm25s.BM25.load(str(bm25_path))

    # ── 公开 API ──────────────────────────────────────────────────────────

    def list_chapters(self) -> list[dict]:
        """返回章节目录。"""
        self.build()
        return [
            {
                "name": info.name,
                "display_name": info.display_name,
                "size_kb": info.size_kb,
                "section_count": info.section_count,
                "summary": info.summary,
            }
            for info in self._chapters.values()
        ]

    def get_chapter_outline(self, chapter: str) -> list[dict]:
        """返回章节的 section 标题列表。"""
        self.build()
        sections = self._sections.get(chapter, [])
        return [
            {
                "section_id": s.section_id,
                "title": s.title,
                "page": s.page,
                "line_start": s.line_start,
            }
            for s in sections
        ]

    def search(self, query: str, top_k: int = 5) -> list[dict]:
        """BM25 搜索，返回匹配的 section 片段。"""
        self.build()
        if not self._bm25_retriever or not self._corpus:
            return []

        import bm25s

        try:
            try:
                stemmer = Stemmer.Stemmer("english")
            except Exception:
                stemmer = None

            query_tokens = bm25s.tokenize(
                [query], stopwords="en", stemmer=stemmer
            )
            results, scores = self._bm25_retriever.retrieve(
                query_tokens, k=min(top_k, len(self._corpus))
            )
        except Exception:
            return []

        hits = []
        for idx, score in zip(results[0], scores[0]):
            if idx < 0 or idx >= len(self._corpus_meta):
                continue
            meta = self._corpus_meta[idx]
            corpus_text = self._corpus[idx]

            # 提取 snippet（前 500 字符）
            snippet = corpus_text[:500]
            if len(corpus_text) > 500:
                snippet += "..."

            hits.append({
                "chapter": meta["chapter"],
                "section_id": meta["section_id"],
                "title": meta["title"],
                "page": meta.get("page"),
                "snippet": snippet,
                "score": float(score),
            })

        return hits

    def get_section(self, chapter: str, section_id: str) -> dict:
        """返回指定 section 的完整内容。"""
        self.build()
        sections = self._sections.get(chapter, [])
        for s in sections:
            if s.section_id == section_id:
                return {
                    "chapter": chapter,
                    "section_id": s.section_id,
                    "title": s.title,
                    "page": s.page,
                    "content": s.content,
                }
        return {"error": f"Section '{section_id}' not found in '{chapter}'"}

    def find_command_docs(self, keyword: str, top_k: int = 5) -> list[dict]:
        """搜索特定命令/关键词的文档位置。"""
        self.build()
        if not self._bm25_retriever or not self._corpus:
            return []

        # 对于精确关键词搜索，直接在 corpus 中查找
        keyword_lower = keyword.lower()
        matches = []
        for idx, text in enumerate(self._corpus):
            if keyword_lower in text.lower():
                meta = self._corpus_meta[idx]
                # 找到关键词周围的上下文
                pos = text.lower().find(keyword_lower)
                start = max(0, pos - 100)
                end = min(len(text), pos + len(keyword) + 200)
                context = text[start:end]
                if start > 0:
                    context = "..." + context
                if end < len(text):
                    context = context + "..."

                matches.append({
                    "chapter": meta["chapter"],
                    "section_id": meta["section_id"],
                    "title": meta["title"],
                    "page": meta.get("page"),
                    "context": context,
                })

        return matches[:top_k]


# ═══════════════════════════════════════════════════════════════════════════
# 模块级工具函数
# ═══════════════════════════════════════════════════════════════════════════

# 延迟导入 Stemmer（只在需要时）
try:
    import Stemmer
except ImportError:
    Stemmer = None  # type: ignore


# 单例缓存
_index_cache: dict[str, ManualIndex] = {}


def get_manual_index(software: str) -> ManualIndex | None:
    """获取指定软件的手册索引（单例缓存，首次调用自动构建 BM25 索引）。"""
    software = software.lower()
    if software in _index_cache:
        return _index_cache[software]

    from pathlib import Path
    project_root = Path(__file__).parent.parent.parent.parent
    manual_dir = project_root / "docs" / "software_manuals" / software

    if not manual_dir.exists():
        return None

    idx = ManualIndex(manual_dir)
    # 首次调用时自动构建索引（内部有缓存机制，已构建则跳过）
    idx.build()
    _index_cache[software] = idx
    return idx
