import markdownIt from "markdown-it";
const md = new markdownIt();

export default async function (eleventyConfig) {
    // Copy the imgs directory to the output
    eleventyConfig.addPassthroughCopy("imgs");

    eleventyConfig.setFrontMatterParsingOptions({
        excerpt: true,
        // Optional, default is "---"
        excerpt_separator: "<!-- excerpt -->",
    });

    eleventyConfig.addFilter("markdown", content => {
        return md.render(content);
    })
};