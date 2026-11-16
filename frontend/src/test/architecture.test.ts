import ts from 'typescript'
import { expect, it } from 'vitest'

function gatewayImports(source: string): string[] {
  const tree = ts.createSourceFile('component.tsx', source, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX)
  const found: string[] = []
  function visit(node: ts.Node) {
    if ((ts.isImportDeclaration(node) || ts.isExportDeclaration(node)) && node.moduleSpecifier && ts.isStringLiteral(node.moduleSpecifier)) {
      if (/\/(api)(\.ts)?$/.test(node.moduleSpecifier.text)) found.push(node.moduleSpecifier.text)
    }
    if (ts.isCallExpression(node) && node.expression.kind === ts.SyntaxKind.ImportKeyword) {
      const path = node.arguments[0]
      if (path && ts.isStringLiteral(path) && /\/api(\.ts)?$/.test(path.text)) found.push(path.text)
    }
    ts.forEachChild(node, visit)
  }
  visit(tree)
  return found
}

it('components and auth providers access the API through hooks', () => {
  const sources = import.meta.glob<string>(['../components/**/*.{ts,tsx}', '../contexts/**/*.{ts,tsx}'], { eager: true, query: '?raw', import: 'default' })
  const violations = Object.entries(sources)
    .flatMap(([path, source]) => gatewayImports(source).map(module => `${path}: ${module}`))
  expect(violations).toEqual([])
})

it('detects direct, re-exported and dynamic gateway imports', () => {
  expect(gatewayImports("import { api } from '../api'; export { api } from '../../api.ts'; const api = import('../api')"))
    .toEqual(['../api', '../../api.ts', '../api'])
  expect(gatewayImports("import type { Invoice } from '../types'; import { useInvoices } from '../hooks/useInvoices'"))
    .toEqual([])
})
