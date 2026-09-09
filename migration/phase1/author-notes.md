# Phase 1 checkpoint author notes

Overall this pilot shows a lot of promise, and it's a good starting point for
our migration efforts. At this point, the HTML site is the main accessibility
target, with PDF accessibility a nice-to-have. The Pyodide computations work
well.

## HTML site

- Keyboard navigation works great in all browsers.
- Mobile renders well.
- Different browsers differ in how well they read the pages, with Microsoft Edge
  doing a great job, Safari on Mobile sounding great, but skipping some maths,
  and Firefox doing poorly generally.
- The display equations typically render with a vertical scrollbar. This should
  be fixed so that only a horizontal scrollbar is displayed, and only when the
  equation is wider than the textwidth.
- On desktops, the textblock shifts to the left when the navigation menu is
  hidden.
- The fonts are inconsistent, with titles and block titles in serifs and the
  body text in sans-serif in a smaller size. Use on serif font through-out, say
  Charter.

## PDF

- Use `\qedhere` (or similar) to ensure end-of-structure markers don't sit on a
  line by themselves. (Examples 1.1, 2.1 and 4.6, Definition 4.1, etc.)
- The rendering differs occasionally between the print and the accessible PDF,
  e.g., the document title, and the “basis” column of Table 5.1 is (wrongly)
  justified in the accessible PDF.

## Remaining gates:

1. The FOP error on `coverage set class table not yet supported` is well known
   and should be ignored for now.
2. Glyph mapping seems good, but let's keep the warnings for now.
3. Acknowledged. The pilot is promising, and everything will be proof-read after
   checked after migration.
4. Accessible PDF is not a requirement at this stage (though this may
   change). We think it's better to do this after the main migration, when the
   tagged LaTeX project is further along, unless advised otherwise.
5. Firefox/WebGL works wells, touch-device behavior is perfect. Legacy iframe overflow not an issue at this stage.
