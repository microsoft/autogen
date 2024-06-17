function findAllNotebooks() {
    const notebooks = [];
    const context = require.context("../../docs/notebooks", true, /\.mdx$/);
    context.keys().forEach((key) => {
        const notebook = context(key);
        // Remove .mdx extension from the key.
        key = key.slice(0, -4);

        notebooks.push({
            title: notebook.frontMatter.title,
            link: "/autogen/docs/notebooks/" + key,
            description: notebook.frontMatter.description,
            image: notebook.frontMatter.image,
            tags: notebook.frontMatter.tags,
            source: notebook.frontMatter.source_notebook
        });
    });
    return notebooks;
}

export {
    findAllNotebooks
};
