import { readdirSync, readFileSync } from 'node:fs'
import { join, relative } from 'node:path'
import { describe, expect, it } from 'vitest'

const root = join(process.cwd(), 'src')

function sourceFiles(dir: string): string[] {
  return readdirSync(dir, { withFileTypes: true }).flatMap(entry => {
    const full = join(dir, entry.name)
    if (entry.isDirectory()) return sourceFiles(full)
    if (!/\.(css|ts|tsx)$/.test(entry.name)) return []
    if (/\.test\.(ts|tsx)$/.test(entry.name) || entry.name === 'setup.ts') return []
    return [full]
  })
}

describe('design token floor', () => {
  it('keeps raw hex colours out of source outside tokens.css', () => {
    const offenders = sourceFiles(root)
      .filter(file => relative(root, file).replaceAll('\\', '/') !== 'styles/tokens.css')
      .flatMap(file => {
        const text = readFileSync(file, 'utf8')
        const hits = text.match(/#[0-9a-fA-F]{3,8}\b/g) ?? []
        return hits.map(hit => `${relative(root, file)}: ${hit}`)
      })
    expect(offenders).toEqual([])
  })

  it('keeps literal font families out of source outside tokens.css', () => {
    const offenders = sourceFiles(root)
      .filter(file => relative(root, file).replaceAll('\\', '/') !== 'styles/tokens.css')
      .flatMap(file => {
        const text = readFileSync(file, 'utf8')
        const hits = text.match(/font-family\s*:\s*(?!\s*var\()[^;}]+/g) ?? []
        return hits.map(hit => `${relative(root, file)}: ${hit.trim()}`)
      })
    expect(offenders).toEqual([])
  })

  it('does not use transition: all', () => {
    const offenders = sourceFiles(root)
      .filter(file => file.endsWith('.css'))
      .filter(file => readFileSync(file, 'utf8').includes('transition: all'))
    expect(offenders).toEqual([])
  })
})
