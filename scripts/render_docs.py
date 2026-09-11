#!/usr/bin/env python3
"""Optional docs builder; needs markdown-it-py. Runtime collectors use only stdlib."""
from pathlib import Path
from markdown_it import MarkdownIt

ROOT=Path(__file__).resolve().parents[1]
md=MarkdownIt('commonmark', {'html':False}).enable('table')
sections=[]
for anchor,filename in [('start','README.md'),('agent','AGENT_HANDOFF.md'),('automation','AUTOMATION_PROMPT.md')]:
    sections.append('<section id="'+anchor+'">'+md.render((ROOT/filename).read_text())+'</section>')
body=''.join(sections).replace('<table>','<div class="table-wrap"><table>').replace('</table>','</table></div>')
css='''*{box-sizing:border-box}body{margin:0;background:#f4f6f5;color:#20342e;font:17px/1.65 system-ui,sans-serif}header{background:#183e35;color:white;padding:40px max(24px,calc((100vw - 1050px)/2));font-size:38px;font-weight:650}nav{display:flex;gap:24px;flex-wrap:wrap;background:white;padding:18px max(24px,calc((100vw - 1050px)/2));border-bottom:1px solid #dde5df}a{color:#17614e;text-underline-offset:3px}main{max-width:1050px;padding:24px;margin:auto}section{background:white;border:1px solid #dce5df;border-radius:12px;padding:36px;margin-bottom:24px}h1{font-size:32px;line-height:1.2}h2{font-size:23px;margin-top:32px}li{margin:10px 0}code{font-size:.86em;overflow-wrap:anywhere;background:#eff3ef;padding:2px 4px}pre{background:#15372e;color:#eaf3ee;overflow:auto;padding:18px;border-radius:8px}pre code{background:none;overflow-wrap:normal}blockquote{border-left:3px solid #8aa899;margin-left:0;padding-left:20px}.table-wrap{overflow:auto}table{border-collapse:collapse;width:100%;font-size:15px}td,th{padding:12px;border-bottom:1px solid #dde5df;text-align:left}th{background:#eef4ef}@media(max-width:600px){main{padding:12px}section{padding:22px 18px}header{font-size:30px}body{font-size:16px}table{min-width:480px}}@media print{header,nav{display:none}main{max-width:none;margin:0;padding:0}section{border:none;break-before:page}pre{white-space:pre-wrap}.table-wrap{overflow:visible}table{min-width:0}}'''
page='<!doctype html><html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Trendwatch · скилл для вашего бренда</title><style>'+css+'</style></head><body><header>Trendwatch</header><nav><a href="#start">Начать</a><a href="#agent">Инструкция агенту</a><a href="#automation">Мониторинг</a></nav><main>'+body+'</main></body></html>'
(ROOT/'index.html').write_text(page)
print('index.html generated')
