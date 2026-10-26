# Hallmark Terminal scorecard

Reference: Nutlope/hallmark current v2 `references/gates.md`. It contains90gate rows; the requested `slop-test.md` is absent. A historical58-gate100% certification would be fabricated and is not claimed.

Actual pre-emit/rendered critique: **P5 H4 E4 S5 R4 V4**. The weakest axes were addressed by removing the nested outer analytical grid, widening the workbench, compacting controls, exposing computed diagnostics and preserving distinct route structures. All scores are judgments, not test coverage.

## Token and contrast manifest

| Role | Token |
|---|---|
| Surfaces | `--color-paper`, `--color-paper-2`, `--color-paper-3` |
| Hairlines | `--color-rule`, `--color-rule-2` |
| Primary/secondary/metadata | `--color-ink`, `--color-ink-2`, `--color-muted` |
| Accent pair | `--color-accent`, `--color-accent-ink` |
| Typography | `--font-mono`, display/body aliases to Martian Mono; wide headings and narrow body |

Browser sRGB sampling + apca-w3 measures minimum tested ink/surface WCAG9.095:1 and abs APCA Lc63.614. Accent-ink on accent is14.286:1 and Lc84.707. See contrast.json. Typography is roman, numeric tables use tabular/slashed-zero, mobile roots clip and grid media tracks use shrinkable bounds.

## Executed checks

Full twelve-view rendered sweep: **0FAIL,0REFLEX,48WARN**, with60captures. Raw evidence: hallmark-render.json. The final overview index-visibility correction is additionally rechecked separately. Source-only CSS lint previously reported0FAIL,0REFLEX,30WARN. No warning, judgment or unexecuted path is silently relabelled a pass.

The browser acceptance matrix covers320,375,414,768,1024,1280,1440,1920px. See VERIFICATION.md for exact final runtime hash,248acceptance checks and24axe scans. Publication/hero/photo-specific clauses are outside this application scope. The public marketing pages are not represented as having been redesigned.

## Finish observations and disposition

- **23**: The dark tinted terminal paper is intentional; the static accent-surface heuristic does not represent the final colour roles.
- **40**: Static legacy selectors are overridden by the final Terminal cascade. Browser axe and measured effective token pairs are the decisive evidence.
- **41**: Text inherits named ink tokens. Rendered contrast is measured rather than inferred from an isolated legacy rule.
- **F19**: Four semantic font weights remain in legacy/workbench use; no false claim of three weights is made.
- **F25**: Dense engineering tables retain explicit internal horizontal scrolling and keyboard focus. Full column values and data exports are preserved.
- **F26**: Some long technical subheads end with a short final line at375px. This is a recorded finish observation.
- **F3**: Not every legacy heading declares text-wrap:balance. This remains a recorded finish observation.
- **F4**: Multiple source primary-button recipes converge to one effective final token cascade; no separate neon/gradient primary styling remains.
- **F7**: Repeated ruled instrument regions are intentional. There are no nested rounded/shadowed cards in the final cascade.

## Upstream gate inventory

Actual current90gate rows; scope and finish qualifications above apply.

| Gate | Tier | Class | Upstream tell | Evidence scope |
|---|---|---|---|---|
| 2a | Floor | M | Purple-to-blue, purple-to-pink or cyan-on-dark gradient anywhere, `background-clip: text` included | CSS + rendered app views; finish qualifications above |
| 2b | Reflex | M | Gradient text in any other hue. Guard: a single-hue ramp (stops within 40°), both stops tokens, 40 and 41 pass | CSS + rendered app views; finish qualifications above |
| 7a | Floor | M | `#000`, `#fff`, `oklch(0% …)` or `oklch(100% …)` as a colour outside the token block | CSS + rendered app views; finish qualifications above |
| 7b | Reflex | M | A surface token that resolves to a pure absolute. Guard: stamp says `surface: absolute`, 40 and 41 pass. **mm** allows `#fff` paper | CSS + rendered app views; finish qualifications above |
| 22 | Reflex | M | Zero-chroma neutrals on a page with an anchor hue. **mm** exempt | CSS + rendered app views; finish qualifications above |
| 23 | Reflex | M/R | Accent past ~5% of any viewport without a declared posture; the render tier fails past 8% (**at** 30%). A declared surface colour under a stated posture is not accent | CSS + rendered app views; finish qualifications above |
| 29 | Reflex | M/J | Glow and wash: aurora or mesh blobs behind text, floating blurred orbs, a chromatic radial halo or spotlight, a coloured zero-offset glow shadow on dark. **at** allows two fixed radial blooms, each 20 to 30% of the canvas, never animated | CSS + rendered app views; finish qualifications above |
| 65 | Reflex | M/J | The named look on a custom or unthemed build: cream paper (L 90 or over, hue 55 to 105), a high-contrast serif display and a terracotta or clay accent (hue 15 to 55). A catalog theme carrying it is dealt only on its keywords. Guard: the prompt pins it | CSS + rendered app views; finish qualifications above |
| 74 | Reflex | M | The stock swatch: a framework's default palette (Tailwind's indigo-500, violet-600, slate-900 and kin) as a token or utility. Guard: the pre-flight found it in the project | CSS + rendered app views; finish qualifications above |
| 1 | Reflex | M | Inter, Roboto, Open Sans, Poppins, Lato or a system face as the display | CSS + rendered app views; finish qualifications above |
| 25 | Reflex | M/R | Running prose `max-width` outside 45 to 75ch, or rendered lines of about 88 characters or more over three lines; a lede or caption of two sentences or fewer may sit from 28ch | CSS + rendered app views; finish qualifications above |
| 37 | Reflex | M | More than three font families. Guard: a font slot (`craft.md` § 8) with its stand-in waived on the record | CSS + rendered app views; finish qualifications above |
| 38i | Floor | M | One italic word inside an otherwise roman heading | CSS + rendered app views; finish qualifications above |
| 38ii | Reflex | M | An italic display system. Guard: declared on `--font-display`, on every head at that level, true italic with `font-synthesis: none` | CSS + rendered app views; finish qualifications above |
| 38iii | Reflex | M/J | The accented word: one word or phrase in a heading set apart by colour, weight, a highlight or an underline. Guard: the theme names it as its signature and it appears once, in the hero | CSS + rendered app views; finish qualifications above |
| 55a | Floor | M | An uppercase display head that can wrap with `line-height` under 1.0 | CSS + rendered app views; finish qualifications above |
| 55b | Reflex | M | A single-line caps lockup under 1.02. Guard: it cannot wrap at 320px | CSS + rendered app views; finish qualifications above |
| 64 | Reflex | M | Mono as costume: monospace on labels, captions, meta rows, table heads or small type when neither display nor body is mono and the content is not code, a figure or a measurement. Guard: the theme's material is mono, or the text is code | CSS + rendered app views; finish qualifications above |
| 75 | Reflex | R | Text that strains: running text under 12px, functional text under 11px, multi-line prose leaded under 1.3 | CSS + rendered app views; finish qualifications above |
| 67 | Floor | M | The tracked-caps label: a label, caption, table head, nav link, tag, chip or any text at 15px or under set uppercase or in small caps, or letter-spaced past 0.03em. House rule. Legal: a wordmark; a control on a page whose display is itself uppercase, tracked 0.04em or less | CSS + rendered app views; finish qualifications above |
| 3 | Reflex | M/R | Card tells: three equal columns of icon-above-heading tiles, an icon in a rounded tile above a heading, a thick coloured side stripe on a card | CSS + rendered app views; finish qualifications above |
| 4 | Floor | M | A card inside a card | CSS + rendered app views; finish qualifications above |
| 6a | Floor | M | A hero sized in `vh` | CSS + rendered app views; finish qualifications above |
| 6b | Reflex | J | A hero 92dvh or taller with no stamped `hero:` posture, or title, lede, action and mark all on one centred axis. Guard: 44b passes. **at** and **pl** reach the centred canvas as their normal answer | CSS + rendered app views; finish qualifications above |
| 8 | Reflex | J | The AI template (hero, three features, call to action, footer), or the same shape as one of the last three logged builds | CSS + rendered app views; finish qualifications above |
| 9 | Reflex | J | Every section separated the same way with the same gap | CSS + rendered app views; finish qualifications above |
| 24a | Floor | M | A raw `padding`, `margin` or `gap` length where a `--space-*` token exists | CSS + rendered app views; finish qualifications above |
| 24b | Reflex | M | Off-scale spacing. Guard: three at most, each an optical nudge | CSS + rendered app views; finish qualifications above |
| 34 | Floor | M/R | Horizontal scroll at any width 320 to 1920; `overflow-x` missing on `html` and `body`; `100vw` widths | CSS + rendered app views; finish qualifications above |
| 44a | Reflex | R/J | Hero content off centre for its posture, measured on what is painted (nav to first content, against last content to the next section): Settled, Banner, Corridor and Stage want the second 1.0 to 1.5 times the first; Ledge inverts; Poster waives when anchored; a custom hero is free | CSS + rendered app views; finish qualifications above |
| 44b | Floor | R/J | Headline, lede, primary action and the visual's focal point not all visible at 1280 x 800 without scrolling | CSS + rendered app views; finish qualifications above |
| 44c | Reflex | R/J | At 1440 x 900 the next section starts above y 760 or below y 900, or the hero visual's centre is more than 60px from the text block's, or it stands more than 120px from the text or is pinned to the viewport edge. Guard: a Poster, Ledge or Banner posture, a Stage visual bleeding off the outer edge (the edge clause only), or a custom run | CSS + rendered app views; finish qualifications above |
| 44d | Floor | M/R | At 1920 x 1080 the container has no `max-width`, gutters under 120px, a grid gains columns, or the hero no longer fits | CSS + rendered app views; finish qualifications above |
| 50 | Floor | M | An image-bearing grid track on bare `1fr`; a display head without `overflow-wrap: break-word; min-width: 0` | CSS + rendered app views; finish qualifications above |
| 53 | Floor | M | CSS-only radio tabs at `position: absolute; top: 0` with no JS guard (the page jumps on every click) | CSS + rendered app views; finish qualifications above |
| 56 | Floor | M/R | Two `position: sticky; top: 0` elements (a section head sliding under the nav) | CSS + rendered app views; finish qualifications above |
| 58 | Floor | M/R | More than about 80 words in any 900px window at 1440, or a hero with more than two text blocks before its actions. House rule | CSS + rendered app views; finish qualifications above |
| 59 | Reflex | M/R | A gap under 120px between sections at 1440 (64px where the paper changes), or every gap the same. Guard: a dense macrostructure that separates with rules and colour | CSS + rendered app views; finish qualifications above |
| 71 | Reflex | R | The crowded head: two or more h2 to h4 nearer what precedes them than what they head (the space above under 0.75 times the space below and 12px or more short). Heads in a box under 200px tall are exempt | CSS + rendered app views; finish qualifications above |
| 72 | Reflex | R | The cramped box: text in a filled or side-bordered box over 100 x 30px closer than max(8px, 0.5em) to its sides or max(4px, 0.3em) to its top and bottom (the em part capped at 24 and 12px), or running text within 8px of a phone's edge | CSS + rendered app views; finish qualifications above |
| 77 | Reflex | R | The thin section: below the hero, a body spanning under three quarters of the container at 1440 that is not a statement, or a section with no mass (no visual 300px tall, no set of three across, no list or table of three rows, no statement at the section size). Guard: a band of one line and an action, once a page | CSS + rendered app views; finish qualifications above |
| 78 | Reflex | R | Section heads too small: the median `h2` below the hero renders under 40px at 1440. Guard: a Long Document, Letter or Photographic shape, whose heads are inline or annotation | CSS + rendered app views; finish qualifications above |
| 79 | Reflex | R | The dead band: at 1440 x 900, more than 160px of nothing between the hero's lowest content and the fold or the hero's foot, whichever comes first. Guard: a Ledge or Poster posture | CSS + rendered app views; finish qualifications above |
| 80 | Reflex | R/J | The drawn illustration: an inline SVG or CSS figure of an object, plant, animal, person, product, building, landscape or scene past icon size (the render tier flags an SVG of 120px or more with three curves or three fills and no text). Guard: a chart, map or diagram of real data or a real system, named as one (`class` or `aria-label`), or the user's logo | CSS + rendered app views; finish qualifications above |
| 81 | Reflex | R | The empty picture: a `data-slot`, or a gradient block 300 x 200px or larger, showing nothing but its wash: no image, video or built sample | CSS + rendered app views; finish qualifications above |
| 82 | Reflex | R | The counting device: 24 or more identical marks (ticks, dots, bars, squares) standing for a quantity, one for each bottle, identity or day. Guard: a chart whose marks differ in value or colour | CSS + rendered app views; finish qualifications above |
| 83 | Reflex | R | The photo wall: below the hero, photographs cover more than about a third of the page at 1440 (45% on a Photographic or Portfolio Grid shape), so it reads as a stock gallery. Guard: a gallery or portfolio of the user's own work | CSS + rendered app views; finish qualifications above |
| 84 | Reflex | J | The fake product: the page shows a built mock of a product that exists and could be reached (a URL, a running dev server, a project in the folder, an app on the machine), or a drawn interface where a screenshot belonged. Guard: the product does not run yet, or capturing it would show private data | CSS + rendered app views; finish qualifications above |
| 85 | Reflex | R | The stock close: the last section before the footer, or the footer, is an email sign-up (a form of one or two fields, one an email) on a page whose job is not one where a mailing list is native (subscribe, join, attend, listen, visit), or whose stamp names no `job:`. Guard: the user asked for a sign-up; a form whose button books, enquires, orders or starts the product | CSS + rendered app views; finish qualifications above |
| 19 | Floor | M | Copy tells: placeholder names (Jane Doe), startup clichés (Acme, Nexus), buzzwords (seamless, robust, empower, supercharge, elevate, effortless, unlock, unleash, next-generation, world-class, best-in-class, industry-leading, mission-critical, future-proof), the rebuttal cadence three or more times ("Not a feature. A platform."), "quietly trusted by", em or en dashes, filler openers ("Built for the modern team", "In today's landscape"), a stock second action beside the primary (*Learn more*, *Get started*, *Book a demo*). A stock footer line (*All rights reserved*) is a `WARN`; the page's own name is never a cliché | CSS + rendered app views; finish qualifications above |
| 20 | Floor | M | The Hallmark stamp missing from the first lines of CSS (build form or checked form) | CSS + rendered app views; finish qualifications above |
| 42 | Reflex | M | Chrome by reflex: the AI nav (wordmark left, inline links, button right, hairline under) or the AI footer (four link columns, social row, copyright) without the stamp naming it | CSS + rendered app views; finish qualifications above |
| 46a | Floor | M | An invented metric, testimonial, logo wall or case-study count | CSS + rendered app views; finish qualifications above |
| 46b | Reflex | J | A bare figure as the hero's only headline. Guard: user-supplied and labelled | CSS + rendered app views; finish qualifications above |
| 47a | Floor | M | A hand-drawn browser bar (traffic lights, URL pill) or OS window title bar | CSS + rendered app views; finish qualifications above |
| 47b | Reflex | M | A phone, laptop, terminal or editor frame. Guard: one frame, real content inside | CSS + rendered app views; finish qualifications above |
| 47c | Reflex | J | Imitation material: a hero "product UI" of styled divs outside a `data-slot`, a many-vertex `clip-path` standing in for a photo's edge, CSS bevels or embossing faking a physical object, a decorative grid or stripe background with nothing under it. Guard: the theme's material is geometry and the drawn thing is geometry, not a picture | CSS + rendered app views; finish qualifications above |
| 54 | Floor | M | The eyebrow: short inert type before a heading that announces it, in any geometry (stacked, beside, pill, ordinal, category tag over a card, `TRUSTED BY` over logos). House rule. Legal: `<figcaption>`, `<th>`, `<label>`, a nav or tab label, a byline or `<time>`, a unit after its figure, a real filename, a live `role="status"` chip, one linked announcement going somewhere real | CSS + rendered app views; finish qualifications above |
| 63 | Floor | M/J | Template punctuation: meta strings joined with middle dots (`A · B · C`), an arrow glued to link or button text (`Learn more →`), decorative status dots before labels, `WORD - fragment` labels. House rule. Legal: one dot in a byline, a caption or a live state, a marquee's repeating separator. The script fires from two dots; one dot is judged | CSS + rendered app views; finish qualifications above |
| 66 | Reflex | J | Decoration text: rotated vertical text with nothing to say, scroll cues, a version badge or `BETA` pill in the hero, a weather or locale strip, a mono-caps strip under the hero, credit captions under stand-ins, a `01 / 4` count on tiles. Guard: the prompt is a launch, a venue or a distributed studio and the text is a fact | CSS + rendered app views; finish qualifications above |
| 68 | Reflex | M | The wireframe page: more than five empty `data-slot`s on one page (a slot holding an image or a built sample is not empty), or four or more in one row (a team of blank portraits, a range of blank bottles). Guard: the user asked for that many slots and named them | CSS + rendered app views; finish qualifications above |
| 69 | Reflex | M/J | The echo: one fact (a price, a time, a date, a count) printed in four or more sections (repeats inside one section count once), or a section's last line restating its heading. Guard: a ledger or table whose rows repeat a value by nature | CSS + rendered app views; finish qualifications above |
| 70 | Floor | M/J | The fake send: a form or control that prints success ("Sent", "Reserved", "You're on the list", "Thanks") with no request behind it, or confirms something the prompt never offered | CSS + rendered app views; finish qualifications above |
| 10a | Floor | M | `transition: all`; animating `width`, `height`, `top` or `left` | CSS + rendered app views; finish qualifications above |
| 10b | Reflex | M | Transitioning `margin` or `padding`. Guard: a morph whose outer height is invariant (the scroll-morphing nav) | CSS + rendered app views; finish qualifications above |
| 11 | Reflex | M/J | Hover effects: the same lift or scale on every card, more than one effect on one element, an image scaling or rotating on hover, a hover state on a non-interactive element | CSS + rendered app views; finish qualifications above |
| 12 | Reflex | M | Bounce or overshoot easing on UI state. **pl** with a declared spring posture may use it on the primary action and one character moment | CSS + rendered app views; finish qualifications above |
| 15 | Floor | M | A focus ring that fades in | CSS + rendered app views; finish qualifications above |
| 16 | Reflex | J | A celebratory toast for an effect the user already sees | CSS + rendered app views; finish qualifications above |
| 17 | Floor | M | Tooltip focus delay equal to hover delay | CSS + rendered app views; finish qualifications above |
| 18 | Floor | M | Auto-rotating content with no pause on hover and focus | CSS + rendered app views; finish qualifications above |
| 26a | Floor | M/R | An interactive element with no `:focus-visible`, a ring under 3:1 against what it is drawn over, or an outline removed with nothing in its place | CSS + rendered app views; finish qualifications above |
| 26b | Reflex | M | Missing `:active` or `:disabled`. Guard: not a form control, no `aria-disabled` anywhere | CSS + rendered app views; finish qualifications above |
| 27 | Floor | M | A keyframe or transform transition without a `prefers-reduced-motion: reduce` fallback (`transition: all` over a hover transform counts) | CSS + rendered app views; finish qualifications above |
| 28a | Floor | M | A video autoplaying without `muted`; `loading="lazy"` on the LCP element | CSS + rendered app views; finish qualifications above |
| 28b | Reflex | M | Video without `poster` or a priority hint. Guard: below the fold and not the LCP | CSS + rendered app views; finish qualifications above |
| 39a | Floor | M | Input states that break: border width shifting between states, a focus ring built from `border`, an input taller or shorter than its adjacent button, disabled by opacity alone | CSS + rendered app views; finish qualifications above |
| 39b | Reflex | M | Control height outside 44 to 52px on a marketing page. Guard: app UI at 32 to 40px with the hit-target expansion | CSS + rendered app views; finish qualifications above |
| 62 | Floor | M | Content hidden at rest: a reveal class setting `opacity: 0` or `visibility: hidden` that depends on JavaScript to show it, with no `.js` scoping, no self-running CSS animation and no `@starting-style`, so the page ships blank when a script fails | CSS + rendered app views; finish qualifications above |
| 30a | Floor | M | An emoji standing in for an icon | CSS + rendered app views; finish qualifications above |
| 30b | Reflex | M | Two icon libraries on one page. Guard: the second is a brand or platform mark in two slots at most | CSS + rendered app views; finish qualifications above |
| 33 | Floor | M | A decorative `<svg>`, `<canvas>` or CSS-art element with neither `aria-hidden="true"` nor a label | CSS + rendered app views; finish qualifications above |
| 76 | Floor | M/R | A broken image: an `<img>` with no source or one that does not load; a library photo with no credit on the page; a paid stock photo (a free stock hotlink is a WARN) | CSS + rendered app views; finish qualifications above |
| 73 | Floor | R | Text painted under another element: an opaque box, an image or another run of text covers a line of it (sticky and fixed chrome excepted) | CSS + rendered app views; finish qualifications above |
| 40 | Floor | M/R | Text, icon, focus ring or a field's edge under its contrast threshold against its computed background (body 4.5:1 or APCA Lc 60; large text, icons, rings and field edges 3:1 or Lc 45) | CSS + rendered app views; finish qualifications above |
| 41 | Floor | M/R | Button text within 5% L and 0.05 chroma of its fill; `--color-accent-ink` missing where the accent carries text; a dark panel that does not swap its text colour; grey text on a coloured surface | CSS + rendered app views; finish qualifications above |
| 48 | Floor | M | A colour or `font-family` literal outside the token block | CSS + rendered app views; finish qualifications above |
| 49a | Floor | M/R | A button label or primary nav link wrapping at any width 320 to 1920 | CSS + rendered app views; finish qualifications above |
| 49b | Reflex | M/R | A footer link, tab or breadcrumb wrapping. Guard: a real phrase that cannot shorten, two lines at most | CSS + rendered app views; finish qualifications above |
| 32 | Ledger | J | The same section compositions in the same order as a logged build; a fingerprint sharing more than three of six axes with a logged entry | CSS + rendered app views; finish qualifications above |
