
# Scientific article using Quarto


This is my template for scientific articles. It is based on the [Quarto](https://quarto.org/). 
Special features are:
- citation via DOI or bibtex
- GitHub action to render the article

# Get Started

Create a repo by clicking on using the template
Install Quarto

## Render the article

Then you can render the article with the following command:
```
quarto render
```
If you have problems to render the article, you can try to render it to html or docx only
```
quarto render --to html
quarto render --to docx
```

## Clean
remove all files ignored in gitignore to clean the directory
```
git clean -x --dry-run writing/
git clean -x -f writing/
```

## Continuous integration
Github action can render the files as test.
If the action run, you can see the pdf `https://github.com/<user>/<reponame>/blob/gh-pages/manuscript.pdf`
DocX and html are also available.

Obviously only if you have access to the repository.