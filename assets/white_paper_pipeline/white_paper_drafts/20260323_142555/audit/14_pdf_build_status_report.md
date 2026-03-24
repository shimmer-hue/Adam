
# PDF Build Status Report

Status: `EXECUTED`

Command:
```bash
latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex
```

Working directory:
`/Users/brianray/Adam/assets/white_paper_pipeline/white_paper_drafts/20260323_142555/latex`

Output PDF:
`/Users/brianray/Adam/assets/white_paper_pipeline/white_paper_drafts/20260323_142555/pdf/eden_whitepaper_v15.pdf`

PDF hash:
`sha256:d02cbb0cc76810145e8302a3e70b7d3d525d4d958a6c98d74916f31226101f59`

Word-count proof:
`8337+61+894 (14/0/5/0) File: /Users/brianray/Adam/assets/white_paper_pipeline/white_paper_drafts/20260323_142555/latex/main.tex`

PDF info summary:
```text
Title:           Adam v1 Whitepaper
Subject:         
Keywords:        
Author:          Codex for the Adam Repository
Creator:         LaTeX with hyperref
Producer:        pdfTeX-1.40.27
CreationDate:    Mon Mar 23 14:37:19 2026 EDT
ModDate:         Mon Mar 23 14:37:19 2026 EDT
Custom Metadata: yes
Metadata Stream: no
Tagged:          no
UserProperties:  no
Suspects:        no
Form:            none
JavaScript:      no
Pages:           20
Encrypted:       no
Page size:       612 x 792 pts (letter)
Page rot:        0
File size:       1512038 bytes
Optimized:       no
PDF version:     1.7
```

Notes:
- build succeeded with non-fatal overfull/underfull box warnings
- citations and figure references resolved after the second `pdflatex` pass
- no bibliography-key failure or fatal LaTeX error remained
