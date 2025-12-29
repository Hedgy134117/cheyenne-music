import { HtmlBasePlugin } from "@11ty/eleventy";

import markdownIt from "markdown-it";
const md = new markdownIt();

export default async function (eleventyConfig) {
    // Copy the imgs directory to the output
    eleventyConfig.addPassthroughCopy("imgs");
    // Copy the fonts directory to the output
    eleventyConfig.addPassthroughCopy("fonts");

    eleventyConfig.setFrontMatterParsingOptions({
        excerpt: true,
        // Optional, default is "---"
        excerpt_separator: "<!-- excerpt -->",
    });

    eleventyConfig.addFilter("markdown", content => {
        return md.render(content);
    })

    eleventyConfig.addPlugin(HtmlBasePlugin);
};