"""Tests for GROBID extraction client."""

import pytest

from reflens.extraction.grobid import GrobidClient

SAMPLE_TEI_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<TEI xmlns="http://www.tei-c.org/ns/1.0">
  <teiHeader>
    <fileDesc>
      <titleStmt>
        <title>Deep Learning for Scientific Discovery</title>
      </titleStmt>
      <sourceDesc>
        <biblStruct>
          <analytic>
            <author>
              <persName>
                <forename>Alice</forename>
                <surname>Smith</surname>
              </persName>
              <affiliation>
                <orgName>MIT</orgName>
              </affiliation>
            </author>
            <author>
              <persName>
                <forename>Bob</forename>
                <surname>Jones</surname>
              </persName>
              <affiliation>
                <orgName>Stanford</orgName>
              </affiliation>
            </author>
            <idno type="DOI">10.1234/test.2024</idno>
          </analytic>
          <monogr>
            <imprint>
              <date when="2024"/>
            </imprint>
          </monogr>
        </biblStruct>
      </sourceDesc>
    </fileDesc>
    <profileDesc>
      <abstract>
        <p>We present a novel approach to deep learning in science.</p>
      </abstract>
    </profileDesc>
  </teiHeader>
  <text>
    <body>
      <div>
        <head>Introduction</head>
        <p>Deep learning has revolutionized many fields.</p>
      </div>
      <div>
        <head>Methods</head>
        <p>We used a transformer architecture.</p>
      </div>
    </body>
    <back>
      <listBibl>
        <biblStruct>
          <analytic>
            <title>Attention Is All You Need</title>
            <author>
              <persName>
                <forename>Ashish</forename>
                <surname>Vaswani</surname>
              </persName>
            </author>
          </analytic>
          <monogr>
            <imprint>
              <date when="2017"/>
            </imprint>
          </monogr>
          <idno type="DOI">10.xxxxx</idno>
        </biblStruct>
      </listBibl>
    </back>
  </text>
</TEI>
"""


class TestGrobidParsing:
    def setup_method(self):
        self.client = GrobidClient("http://localhost:8070")

    def test_parse_title(self):
        paper = self.client._parse_tei(SAMPLE_TEI_XML)
        assert paper.title == "Deep Learning for Scientific Discovery"

    def test_parse_authors(self):
        paper = self.client._parse_tei(SAMPLE_TEI_XML)
        assert len(paper.authors) == 2
        assert paper.authors[0].name == "Alice Smith"
        assert paper.authors[0].affiliations == ["MIT"]
        assert paper.authors[1].name == "Bob Jones"

    def test_parse_abstract(self):
        paper = self.client._parse_tei(SAMPLE_TEI_XML)
        assert "novel approach" in paper.abstract

    def test_parse_doi(self):
        paper = self.client._parse_tei(SAMPLE_TEI_XML)
        assert paper.doi == "10.1234/test.2024"

    def test_parse_year(self):
        paper = self.client._parse_tei(SAMPLE_TEI_XML)
        assert paper.year == 2024

    def test_parse_sections(self):
        paper = self.client._parse_tei(SAMPLE_TEI_XML)
        assert "Introduction" in paper.sections
        assert "Methods" in paper.sections
        assert "revolutionized" in paper.sections["Introduction"]

    def test_parse_references(self):
        paper = self.client._parse_tei(SAMPLE_TEI_XML)
        assert len(paper.references) == 1
        ref = paper.references[0]
        assert ref.title == "Attention Is All You Need"
        assert ref.year == 2017
        assert "Vaswani" in ref.authors

    def test_full_text_assembled(self):
        paper = self.client._parse_tei(SAMPLE_TEI_XML)
        assert len(paper.full_text) > 0
        assert "revolutionized" in paper.full_text
