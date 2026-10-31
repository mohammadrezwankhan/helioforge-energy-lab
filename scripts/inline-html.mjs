/** Replacement callbacks keep JavaScript/CSS dollar tokens literal in HTML templates. */
export function inlineDashboard(html,{css,js,favicon}){
  return html.replace('<link rel="icon" href="favicon.svg" type="image/svg+xml">',()=>`<link rel="icon" href="data:image/svg+xml,${encodeURIComponent(favicon)}" type="image/svg+xml">`)
    .replace('<link rel="stylesheet" href="styles.css">',()=>`<style>${css}</style>`)
    .replace('<script src="app.js" defer></script>',()=>`<script>${js.replace(/<\/script/gi,match=>'<\\/'+match.slice(2))}</script>`);
}
