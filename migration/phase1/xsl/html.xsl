<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:str="http://exslt.org/strings"
    exclude-result-prefixes="str">
  <!-- The CLI resolves core relative to the custom stylesheet. -->
  <xsl:import href="./core/pretext-html.xsl"/>

  <xsl:param name="html.css.extra" select="'external/pilot/compat.css'"/>
  <xsl:param name="html.js.extra"
      select="'external/pilot/compat.js external/pilot/python-adapter.js'"/>

  <!-- Leave remark and all other proofs governed by publication defaults. -->
  <xsl:template match="insight|warning|proof[@xml:id='pilot-product-invertible-proof']"
      mode="is-hidden">
    <xsl:text>false</xsl:text>
  </xsl:template>

  <xsl:template match="paragraphs[@xml:id='pilot-multilinearity']" mode="is-hidden">
    <xsl:text>true</xsl:text>
  </xsl:template>

  <!-- Preserve the core footnote markup, but follow generic block ID rules:
       only originals own IDs, and a hidden body does not repeat its owner's. -->
  <xsl:template match="fn">
    <xsl:param name="b-original" select="true()"/>
    <xsl:param name="heading-level"/>
    <details class="ptx-footnote" aria-live="polite">
      <xsl:if test="$b-original">
        <xsl:apply-templates select="." mode="html-id-attribute"/>
      </xsl:if>
      <summary class="ptx-footnote__number">
        <xsl:attribute name="title">
          <xsl:apply-templates select="." mode="tooltip-text"/>
        </xsl:attribute>
        <xsl:apply-templates select="." mode="heading-birth">
          <xsl:with-param name="heading-level" select="$heading-level"/>
        </xsl:apply-templates>
      </summary>
      <xsl:apply-templates select="." mode="body">
        <xsl:with-param name="block-type" select="'hidden'"/>
        <xsl:with-param name="b-original" select="$b-original"/>
        <xsl:with-param name="heading-level" select="$heading-level"/>
      </xsl:apply-templates>
    </details>
  </xsl:template>

  <!-- 2.52.3 tokenizes CSS extras, but its JS footer accepts only one URL.
       Extend that existing hook using the same comma/space separators. -->
  <xsl:template name="extra-js-footer">
    <xsl:for-each select="str:tokenize($html.js.extra, ', ')">
      <script src="{.}"></script>
    </xsl:for-each>
  </xsl:template>

  <!-- 2.52.3 loads MathJax 4 from the floating "mathjax@4" tag, so the book's
       mathematics could change under a CDN release without any change here.
       This is the upstream "mathjax" template with the version pinned; nothing
       else differs, and a phase2 test hashes the upstream template so an
       upstream change to it fails rather than being silently overridden. -->
  <xsl:param name="mathjax.version" select="'4.1.3'"/>

  <xsl:template name="mathjax">
    <script type="module">
      <xsl:text>import { startMathJax } from '</xsl:text>
      <xsl:if test="$cdn-prefix = ''">
        <xsl:text>./</xsl:text>
      </xsl:if>
      <xsl:value-of select="$html.js.dir"/>
      <xsl:text>/mathjax_startup.js';&#xa;</xsl:text>
      <xsl:text>startMathJax({&#xa;</xsl:text>
      <xsl:text>hasWebworkReps: </xsl:text><xsl:value-of select="$b-has-webwork-reps"/><xsl:text>,&#xa;</xsl:text>
      <xsl:text>hasSage: </xsl:text><xsl:value-of select="$b-has-sage"/><xsl:text>,&#xa;</xsl:text>
      <xsl:text>isReact: </xsl:text><xsl:value-of select="$b-debug-react"/><xsl:text>,&#xa;</xsl:text>
      <xsl:text>htmlPresentation: </xsl:text><xsl:value-of select="$b-html-presentation"/><xsl:text>,&#xa;</xsl:text>
      <xsl:text>lang: "</xsl:text><xsl:value-of select="$document-language"/><xsl:text>",&#xa;</xsl:text>
      <xsl:text>});&#xa;</xsl:text>
    </script>
    <script defer="true">
      <xsl:attribute name="src">
        <xsl:text>https://cdn.jsdelivr.net/npm/mathjax@</xsl:text>
        <xsl:value-of select="$mathjax.version"/>
        <xsl:text>/</xsl:text>
        <xsl:choose>
          <xsl:when test="$debug.mathjax.svg = 'yes'">
            <xsl:text>tex-svg.js</xsl:text>
          </xsl:when>
          <xsl:otherwise>
            <xsl:text>tex-mml-chtml.js</xsl:text>
          </xsl:otherwise>
        </xsl:choose>
      </xsl:attribute>
    </script>
  </xsl:template>
</xsl:stylesheet>
