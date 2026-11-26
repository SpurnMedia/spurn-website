#!/usr/bin/env python3
"""Build an allowlisted public Pages artifact; never package private materials."""
from __future__ import annotations
import argparse
import shutil
from pathlib import Path

PUBLIC_DIRS = frozenset({"latest","discovery","intelligence","editorial","assets","search","trust"})
PUBLIC_ROOT = frozenset({"index.html","styles.css","article.css","archive.css","script.js",
    "newsletter-config.js","newsletter.js","favicon.svg","Spurn-logo.svg","Spurn-logo.png",
    "Spurn-wordmark.png","robots.txt","sitemap.xml","CNAME"})
PUBLIC_EXT = frozenset({".html",".css",".js",".json",".png",".jpg",".jpeg",".webp",
    ".svg",".gif",".ico",".xml",".txt"})

class BuildError(ValueError):
    pass

def assemble(source: Path, output: Path) -> list[str]:
    source,output=source.resolve(),output.resolve()
    if not (source/"index.html").is_file() or not (source/"CNAME").is_file():
        raise BuildError("site root or custom domain missing")
    if source==output or output.is_relative_to(source) or source.is_relative_to(output):
        raise BuildError("output and source directories must be separate")
    if output.exists():
        raise BuildError("output directory must be absent, not overwritten")
    selected=[]
    for path in source.rglob("*"):
        if path.is_symlink():
            if path.relative_to(source).parts[0] not in {".git",".github"}:
                raise BuildError("symlink in public site: "+str(path))
            continue
        if not path.is_file():
            continue
        rel=path.relative_to(source)
        if rel.as_posix() in {"README.md",".gitignore",".nojekyll"} or rel.name==".gitkeep":
            continue
        if rel.parts[0] in {".git",".github","scripts","docs","tests","dist","build"}:
            continue
        if len(rel.parts)==1:
            if rel.name not in PUBLIC_ROOT:
                raise BuildError("unapproved file at site root: "+rel.as_posix())
        elif rel.parts[0] not in PUBLIC_DIRS:
            raise BuildError("unexpected site directory: "+rel.as_posix())
        elif any(part.startswith(".") for part in rel.parts) or path.suffix.lower() not in PUBLIC_EXT:
            raise BuildError("unexpected public file: "+rel.as_posix())
        selected.append(rel)
    output.mkdir(parents=True)
    try:
        for rel in sorted(selected):
            dest=output/rel
            dest.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(source/rel,dest)
        (output/".nojekyll").write_text("",encoding="utf-8")
        if (output/"CNAME").read_text(encoding="utf-8").strip()!="spurnmedia.com":
            raise BuildError("unexpected public domain")
    except Exception:
        shutil.rmtree(output)
        raise
    return [r.as_posix() for r in sorted(selected)]

def main() -> None:
    p=argparse.ArgumentParser()
    p.add_argument("--source",type=Path,default=Path("."))
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    files=assemble(args.source,args.output)
    print("Public-only Pages artifact built: "+str(len(files))+" files")

if __name__=="__main__":
    main()
