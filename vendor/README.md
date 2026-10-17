# Vendored: Cytoscape.js

| Field | Value |
|---|---|
| Upstream | [cytoscape/cytoscape.js](https://github.com/cytoscape/cytoscape.js) |
| Version | pinned in `VERSION` (see that file — the exact release the site ships) |
| File | `cytoscape.min.js` (`dist/cytoscape.min.js` of that release) |
| Licence | MIT (the minified file carries the upstream copyright header) |
| Fetched from | `https://cdn.jsdelivr.net/npm/cytoscape@<version>/dist/cytoscape.min.js` |

Committed on purpose: the site must work on GitHub Pages (and offline) with no
build step, no CDN dependency and no GitHub Actions. To refresh:

```bash
V=$(curl -s "https://data.jsdelivr.com/v1/packages/npm/cytoscape/resolved?specifier=3" \
     | python3 -c "import json,sys; print(json.load(sys.stdin)['version'])")
curl -sL "https://cdn.jsdelivr.net/npm/cytoscape@$V/dist/cytoscape.min.js" -o cytoscape.min.js
echo "$V" > VERSION
```
