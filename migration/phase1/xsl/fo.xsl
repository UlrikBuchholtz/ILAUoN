<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:exsl="http://exslt.org/common"
    xmlns:pi="http://pretextbook.org/2020/pretext/internal"
    exclude-result-prefixes="exsl pi">
  <xsl:import href="./core/pretext-fo.xsl"/>

  <!-- Core's static assembly drops the interactive's description when it
       manufactures preview and QR images. Keep its layout and image renderer. -->
  <xsl:template match="interactive[not(static)][normalize-space(shortdescription) != '']"
      mode="representations">
    <xsl:variable name="static"><xsl:apply-imports/></xsl:variable>
    <xsl:apply-templates select="exsl:node-set($static)/node()" mode="pilot-static-alt">
      <xsl:with-param name="description" select="normalize-space(shortdescription)"/>
    </xsl:apply-templates>
  </xsl:template>

  <xsl:template match="@*|node()" mode="pilot-static-alt">
    <xsl:param name="description"/>
    <xsl:copy>
      <xsl:apply-templates select="@*|node()" mode="pilot-static-alt">
        <xsl:with-param name="description" select="$description"/>
      </xsl:apply-templates>
    </xsl:copy>
  </xsl:template>

  <xsl:template match="image[not(shortdescription)][not(@decorative = 'yes')]"
      mode="pilot-static-alt" name="pilot-static-image-description">
    <xsl:param name="description"/>
    <xsl:copy>
      <xsl:copy-of select="@*|node()"/>
      <shortdescription>
        <xsl:choose>
          <xsl:when test="starts-with(@pi:generated, 'qrcode/')">
            <xsl:text>QR code for interactive: </xsl:text>
          </xsl:when>
          <xsl:otherwise><xsl:text>Preview of interactive: </xsl:text></xsl:otherwise>
        </xsl:choose>
        <xsl:value-of select="$description"/>
      </shortdescription>
    </xsl:copy>
  </xsl:template>
</xsl:stylesheet>
