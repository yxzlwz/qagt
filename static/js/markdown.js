function render_md(markdown) {
    let rendererMD = new marked.Renderer();
    marked.setOptions({
        renderer: rendererMD,
        gfm: true,
        tables: true,
        breaks: false,
        pedantic: false,
        sanitize: false,
        smartLists: true,
        smartypants: false,
        /* highlight: function (code) {
            return hljs.highlightAuto(code).value;
        } */
    });

    // return marked(markdown.replace(/</g, "&lt;").replace(/>/g, "&gt;"));
    return marked(markdown);
}