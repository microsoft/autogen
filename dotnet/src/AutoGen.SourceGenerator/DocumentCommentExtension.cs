// Copyright (c) Microsoft Corporation. All rights reserved.
// DocumentCommentExtension.cs

using System;
using System.Collections.Generic;
using System.Linq;
using System.Xml.Linq;
using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.CSharp;
using Microsoft.CodeAnalysis.CSharp.Syntax;

// copyright: https://github.com/DotNetAnalyzers/StyleCopAnalyzers/blob/master/StyleCop.Analyzers/StyleCop.Analyzers/Helpers/DocumentationCommentExtensions.cs#L17
namespace AutoGen.SourceGenerator;

internal static class DocumentCommentExtension
{
    public static bool IsMissingOrDefault(this SyntaxToken token)
    {
        return token.IsKind(SyntaxKind.None)
            || token.IsMissing;
    }

    public static string? GetParameterDescriptionFromDocumentationCommentTriviaSyntax(this DocumentationCommentTriviaSyntax documentationCommentTrivia, string parameterName)
    {
        var parameterElements = documentationCommentTrivia.Content.GetXmlElements("param");

        var parameter = parameterElements.FirstOrDefault(element =>
        {
            var xml = XElement.Parse(element.ToString());
            var nameAttribute = xml.Attribute("name");
            return nameAttribute != null && nameAttribute.Value == parameterName;
        });

        if (parameter is not null)
        {
            var xml = XElement.Parse(parameter.ToString());

            return xml.Nodes().OfType<XText>().FirstOrDefault()?.Value;
        }

        return null;
    }

    public static string? GetNamespaceNameFromClassDeclarationSyntax(this ClassDeclarationSyntax classDeclaration)
    {
        return classDeclaration.Parent is NamespaceDeclarationSyntax namespaceDeclarationSyntax ? namespaceDeclarationSyntax.Name.ToString()
                    : classDeclaration.Parent is FileScopedNamespaceDeclarationSyntax fileScopedNamespaceDeclarationSyntax ? fileScopedNamespaceDeclarationSyntax.Name.ToString()
                    : null;
    }

    public static DocumentationCommentTriviaSyntax? GetDocumentationCommentTriviaSyntax(this SyntaxNode node)
    {
        if (node == null)
        {
            return null;
        }

        foreach (var leadingTrivia in node.GetLeadingTrivia())
        {
            if (leadingTrivia.GetStructure() is DocumentationCommentTriviaSyntax structure)
            {
                return structure;
            }
        }

        return null;
    }

    public static XmlNodeSyntax GetFirstXmlElement(this SyntaxList<XmlNodeSyntax> content, string elementName)
    {
        return content.GetXmlElements(elementName).FirstOrDefault();
    }

    public static IEnumerable<XmlNodeSyntax> GetXmlElements(this SyntaxList<XmlNodeSyntax> content, string elementName)
    {
        foreach (XmlNodeSyntax syntax in content)
        {
            if (syntax is XmlEmptyElementSyntax emptyElement)
            {
                if (string.Equals(elementName, emptyElement.Name.ToString(), StringComparison.Ordinal))
                {
                    yield return emptyElement;
                }

                continue;
            }

            if (syntax is XmlElementSyntax elementSyntax)
            {
                if (string.Equals(elementName, elementSyntax.StartTag?.Name?.ToString(), StringComparison.Ordinal))
                {
                    yield return elementSyntax;
                }

                continue;
            }
        }
    }

    public static T ReplaceExteriorTrivia<T>(this T node, SyntaxTrivia trivia)
        where T : XmlNodeSyntax
    {
        // Make sure to include a space after the '///' characters.
        SyntaxTrivia triviaWithSpace = SyntaxFactory.DocumentationCommentExterior(trivia.ToString() + " ");

        return node.ReplaceTrivia(
            node.DescendantTrivia(descendIntoTrivia: true).Where(i => i.IsKind(SyntaxKind.DocumentationCommentExteriorTrivia)),
            (originalTrivia, rewrittenTrivia) => SelectExteriorTrivia(rewrittenTrivia, trivia, triviaWithSpace));
    }

    public static SyntaxList<XmlNodeSyntax> WithoutFirstAndLastNewlines(this SyntaxList<XmlNodeSyntax> summaryContent)
    {
        if (summaryContent.Count == 0)
        {
            return summaryContent;
        }

        if (!(summaryContent[0] is XmlTextSyntax firstSyntax))
        {
            return summaryContent;
        }

        if (!(summaryContent[summaryContent.Count - 1] is XmlTextSyntax lastSyntax))
        {
            return summaryContent;
        }

        SyntaxTokenList firstSyntaxTokens = firstSyntax.TextTokens;

        int removeFromStart;
        if (IsXmlNewLine(firstSyntaxTokens[0]))
        {
            removeFromStart = 1;
        }
        else
        {
            if (!IsXmlWhitespace(firstSyntaxTokens[0]))
            {
                return summaryContent;
            }

            if (!IsXmlNewLine(firstSyntaxTokens[1]))
            {
                return summaryContent;
            }

            removeFromStart = 2;
        }

        SyntaxTokenList lastSyntaxTokens = lastSyntax.TextTokens;

        int removeFromEnd;
        if (IsXmlNewLine(lastSyntaxTokens[lastSyntaxTokens.Count - 1]))
        {
            removeFromEnd = 1;
        }
        else
        {
            if (!IsXmlWhitespace(lastSyntaxTokens[lastSyntaxTokens.Count - 1]))
            {
                return summaryContent;
            }

            if (!IsXmlNewLine(lastSyntaxTokens[lastSyntaxTokens.Count - 2]))
            {
                return summaryContent;
            }

            removeFromEnd = 2;
        }

        for (int i = 0; i < removeFromStart; i++)
        {
            firstSyntaxTokens = firstSyntaxTokens.RemoveAt(0);
        }

        if (firstSyntax == lastSyntax)
        {
            lastSyntaxTokens = firstSyntaxTokens;
        }

        for (int i = 0; i < removeFromEnd; i++)
        {
            if (!lastSyntaxTokens.Any())
            {
                break;
            }

            lastSyntaxTokens = lastSyntaxTokens.RemoveAt(lastSyntaxTokens.Count - 1);
        }

        summaryContent = summaryContent.RemoveAt(summaryContent.Count - 1);
        if (lastSyntaxTokens.Count != 0)
        {
            summaryContent = summaryContent.Add(lastSyntax.WithTextTokens(lastSyntaxTokens));
        }

        if (firstSyntax != lastSyntax)
        {
            summaryContent = summaryContent.RemoveAt(0);
            if (firstSyntaxTokens.Count != 0)
            {
                summaryContent = summaryContent.Insert(0, firstSyntax.WithTextTokens(firstSyntaxTokens));
            }
        }

        if (summaryContent.Count > 0)
        {
            // Make sure to remove the leading trivia
            summaryContent = summaryContent.Replace(summaryContent[0], summaryContent[0].WithLeadingTrivia());

            // Remove leading spaces (between the <para> start tag and the start of the paragraph content)
            if (summaryContent[0] is XmlTextSyntax firstTextSyntax && firstTextSyntax.TextTokens.Count > 0)
            {
                SyntaxToken firstTextToken = firstTextSyntax.TextTokens[0];
                string firstTokenText = firstTextToken.Text;
                string trimmed = firstTokenText.TrimStart();
                if (trimmed != firstTokenText)
                {
                    SyntaxToken newFirstToken = SyntaxFactory.Token(
                        firstTextToken.LeadingTrivia,
                        firstTextToken.Kind(),
                        trimmed,
                        firstTextToken.ValueText.TrimStart(),
                        firstTextToken.TrailingTrivia);

                    summaryContent = summaryContent.Replace(firstTextSyntax, firstTextSyntax.ReplaceToken(firstTextToken, newFirstToken));
                }
            }
        }

        return summaryContent;
    }

    public static bool IsXmlNewLine(this SyntaxToken node)
    {
        return node.IsKind(SyntaxKind.XmlTextLiteralNewLineToken);
    }

    public static bool IsXmlWhitespace(this SyntaxToken node)
    {
        return node.IsKind(SyntaxKind.XmlTextLiteralToken)
            && string.IsNullOrWhiteSpace(node.Text);
    }

    /// <summary>
    /// Adjust the leading and trailing trivia associated with <see cref="SyntaxKind.XmlTextLiteralNewLineToken"/>
    /// tokens to ensure the formatter properly indents the exterior trivia.
    /// </summary>
    /// <typeparam name="T">The type of syntax node.</typeparam>
    /// <param name="node">The syntax node to adjust tokens.</param>
    /// <returns>A <see cref="SyntaxNode"/> equivalent to the input <paramref name="node"/>, adjusted by moving any
    /// trailing trivia from <see cref="SyntaxKind.XmlTextLiteralNewLineToken"/> tokens to be leading trivia of the
    /// following token.</returns>
    public static T AdjustDocumentationCommentNewLineTrivia<T>(this T node)
        where T : SyntaxNode
    {
        var tokensForAdjustment =
            from token in node.DescendantTokens()
            where token.IsKind(SyntaxKind.XmlTextLiteralNewLineToken)
            where token.HasTrailingTrivia
            let next = token.GetNextToken(includeZeroWidth: true, includeSkipped: true, includeDirectives: true, includeDocumentationComments: true)
            where !next.IsMissingOrDefault()
            select new KeyValuePair<SyntaxToken, SyntaxToken>(token, next);

        Dictionary<SyntaxToken, SyntaxToken> replacements = new Dictionary<SyntaxToken, SyntaxToken>();
        foreach (var pair in tokensForAdjustment)
        {
            replacements[pair.Key] = pair.Key.WithTrailingTrivia();
            replacements[pair.Value] = pair.Value.WithLeadingTrivia(pair.Value.LeadingTrivia.InsertRange(0, pair.Key.TrailingTrivia));
        }

        return node.ReplaceTokens(replacements.Keys, (originalToken, rewrittenToken) => replacements[originalToken]);
    }

    public static XmlNameSyntax? GetName(this XmlNodeSyntax element)
    {
        return (element as XmlElementSyntax)?.StartTag?.Name
            ?? (element as XmlEmptyElementSyntax)?.Name;
    }

    private static SyntaxTrivia SelectExteriorTrivia(SyntaxTrivia rewrittenTrivia, SyntaxTrivia trivia, SyntaxTrivia triviaWithSpace)
    {
        // if the trivia had a trailing space, make sure to preserve it
        if (rewrittenTrivia.ToString().EndsWith(" "))
        {
            return triviaWithSpace;
        }

        // otherwise the space is part of the leading trivia of the following token, so don't add an extra one to
        // the exterior trivia
        return trivia;
    }
}
