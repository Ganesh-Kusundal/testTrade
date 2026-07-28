/**
 * PortfolioPanel — Bloomberg-style trading desk view.
 *
 * Bloomberg plan Module 10: positions, PnL, margins, execution log,
 * and live gate FSM status. All data comes from the backend REST
 * endpoints — no mock fallbacks. Fail-closed: each section renders an
 * honest error state when its endpoint is unreachable.
 */

import { useEffect, useState } from 'react'
import {
  Wallet, Activity, Shield, BookOpen, AlertTriangle,
} from 'lucide-react'
import {
  getPositions, getMargins, getFills, getStrategyStatus,
} from '@/api/client'
import { cn, formatIN, formatNumber, formatTime, pnlColor } from '@/lib/utils'
import type {
  PortfolioPosition, Margins, FillRecord, StrategyStatus,
} from '@/types'

interface PortfolioPanelProps {
  height?: number
}

const POLL_MS = 3000

export function PortfolioPanel({ height = 520 }: PortfolioPanelProps) {
  const [positions, setPositions] = useState<PortfolioPosition[] | null>(null)
  const [margins, setMargins] = useState<Margins | null>(null)
  const [fills, setFills] = useState<FillRecord[] | null>(null)
  const [strategies, setStrategies] = useState<StrategyStatus[] | null>(null)
  const [errors, setErrors] = useState<Record<string, string>>({})

  useEffect(() => {
    let cancelled = false
    const refresh = async () => {
      const next: Record<string, string> = {}
      const [pos, mar, fi, st] = await Promise.allSettled([
        getPositions(), getMargins(), getFills(), getStrategyStatus(),
      ])
      if (cancelled) return
      if (pos.status === 'fulfilled') setPositions(pos.value)
      else next.positions = reason(pos.reason)
      if (mar.status === 'fulfilled') setMargins(mar.value)
      else next.margins = reason(mar.reason)
      if (fi.status === 'fulfilled') setFills(fi.value)
      else next.fills = reason(fi.reason)
      if (st.status === 'fulfilled') setStrategies(st.value)
      else next.strategies = reason(st.reason)
      setErrors(next)
    }
    refresh()
    const id = window.setInterval(refresh, POLL_MS)
    return () => { cancelled = true; clearInterval(id) }
  }, [])

  const totalPnl = (positions ?? []).reduce(
    (s, p) => s + parseFloat(p.total_pnl), 0,
  )

  return (
    <div className="flex flex-col b-panel rounded-sm overflow-hidden" style={{ height }}>
      {/* Header */}
      <div className="flex items-center justify-between px-2 py-1 border-b border-bline bg-bbg2">
        <div className="flex items-center gap-1.5 text-2xs font-semibold uppercase tracking-wider">
          <Wallet className="h-3 w-3 text-bcy" />
          <span>Portfolio</span>
        </div>
        <div className="flex items-center gap-2 font-mono num text-2xs">
          <span className="text-fg-dim">Net P&amp;L</span>
          <span className={cn('font-semibold', pnlColor(totalPnl))}>
            {totalPnl >= 0 ? '+' : ''}{formatIN(totalPnl)}
          </span>
        </div>
      </div>

      {/* Margins strip */}
      <div className="grid grid-cols-3 border-b border-bline text-2xs">
        <MarginCell label="Available" value={margins?.available_margin} error={errors.margins} />
        <MarginCell label="Used" value={margins?.used_margin} error={errors.margins} />
        <MarginCell label="Total" value={margins?.total_balance} error={errors.margins} />
      </div>

      <div className="flex-1 min-h-0 overflow-y-auto">
        {/* Positions */}
        <Section title="Positions" icon={<Activity className="h-3 w-3" />} error={errors.positions}>
          {positions && positions.length > 0 ? (
            <table className="w-full text-2xs font-mono num">
              <thead className="sticky top-0 bg-bbg2 text-fg-dim text-[10px] uppercase tracking-wider">
                <tr>
                  <th className="px-2 py-0.5 text-left">Symbol</th>
                  <th className="px-1 py-0.5 text-right">Qty</th>
                  <th className="px-1 py-0.5 text-right">Avg</th>
                  <th className="px-1 py-0.5 text-right">LTP</th>
                  <th className="px-1 py-0.5 text-right">P&amp;L</th>
                </tr>
              </thead>
              <tbody>
                {positions.map((p) => {
                  const pnl = parseFloat(p.total_pnl)
                  return (
                    <tr key={p.symbol} className="border-b border-bline-subtle/40">
                      <td className="px-2 py-0.5 font-semibold">{p.symbol}</td>
                      <td className={cn('px-1 py-0.5 text-right', pnlColor(p.quantity))}>
                        {p.quantity}
                      </td>
                      <td className="px-1 py-0.5 text-right">{formatIN(parseFloat(p.avg_price))}</td>
                      <td className="px-1 py-0.5 text-right">{formatIN(parseFloat(p.ltp))}</td>
                      <td className={cn('px-1 py-0.5 text-right font-semibold', pnlColor(pnl))}>
                        {pnl >= 0 ? '+' : ''}{formatIN(pnl)}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          ) : positions && positions.length === 0 ? (
            <div className="px-2 py-3 text-center text-fg-dim text-2xs">flat</div>
          ) : (
            <Fallback text="positions unavailable" />
          )}
        </Section>

        {/* Execution log */}
        <Section title="Execution Log" icon={<BookOpen className="h-3 w-3" />} error={errors.fills}>
          {fills && fills.length > 0 ? (
            <table className="w-full text-2xs font-mono num">
              <thead className="sticky top-0 bg-bbg2 text-fg-dim text-[10px] uppercase tracking-wider">
                <tr>
                  <th className="px-2 py-0.5 text-left">Time</th>
                  <th className="px-1 py-0.5 text-left">Symbol</th>
                  <th className="px-1 py-0.5 text-left">Side</th>
                  <th className="px-1 py-0.5 text-right">Qty</th>
                  <th className="px-1 py-0.5 text-right">Price</th>
                </tr>
              </thead>
              <tbody>
                {fills.slice(0, 20).map((f) => (
                  <tr
                    key={f.fillId}
                    className={cn(
                      'border-b border-bline-subtle/40',
                      f.side === 'BUY' ? 'text-bull' : 'text-bear',
                    )}
                  >
                    <td className="px-2 py-0.5 text-fg-muted">
                      {f.ts != null ? formatTime(f.ts, true) : '—'}
                    </td>
                    <td className="px-1 py-0.5 font-semibold">{f.symbol}</td>
                    <td className="px-1 py-0.5">{f.side}</td>
                    <td className="px-1 py-0.5 text-right">{formatNumber(f.quantity)}</td>
                    <td className="px-1 py-0.5 text-right">{formatIN(f.price)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : fills && fills.length === 0 ? (
            <div className="px-2 py-3 text-center text-fg-dim text-2xs">no fills today</div>
          ) : (
            <Fallback text="fills unavailable" />
          )}
        </Section>

        {/* Gate FSM status */}
        <Section title="Gate FSM" icon={<Shield className="h-3 w-3" />} error={errors.strategies}>
          {strategies && strategies.length > 0 ? (
            <div className="divide-y divide-bline-subtle/40">
              {strategies.map((s) => (
                <div key={s.symbol} className="px-2 py-1">
                  <div className="flex items-center justify-between text-2xs">
                    <span className="font-semibold">{s.symbol}</span>
                    <span className="font-mono num text-fg-dim">
                      {s.trade_count}/{s.max_trades_per_day}
                    </span>
                  </div>
                  {s.gates.length > 0 ? (
                    <div className="mt-1 flex flex-wrap gap-1">
                      {s.gates.map((g) => (
                        <span
                          key={g.gate}
                          title={g.reason}
                          className={cn(
                            'px-1 py-0.5 text-[10px] font-mono rounded-sm border',
                            g.passed
                              ? 'bg-bull/15 border-bull/30 text-bull'
                              : 'bg-bear/15 border-bear/30 text-bear',
                          )}
                        >
                          {g.gate}
                        </span>
                      ))}
                    </div>
                  ) : (
                    <div className="mt-1 text-[10px] text-fg-dim">no evaluation yet</div>
                  )}
                </div>
              ))}
            </div>
          ) : strategies && strategies.length === 0 ? (
            <div className="px-2 py-3 text-center text-fg-dim text-2xs">no strategies wired</div>
          ) : (
            <Fallback text="trading not enabled" />
          )}
        </Section>
      </div>
    </div>
  )
}

function Section({
  title, icon, error, children,
}: { title: string; icon: React.ReactNode; error?: string; children: React.ReactNode }) {
  return (
    <div className="border-b border-bline">
      <div className="flex items-center justify-between px-2 py-1 bg-bbg2">
        <div className="flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-wider text-fg-dim">
          {icon}
          <span>{title}</span>
        </div>
        {error && (
          <span className="flex items-center gap-0.5 text-[10px] text-warning">
            <AlertTriangle className="h-2.5 w-2.5" />{error}
          </span>
        )}
      </div>
      {children}
    </div>
  )
}

function MarginCell({ label, value, error }: { label: string; value?: number; error?: string }) {
  return (
    <div className="px-2 py-1 border-r last:border-r-0 border-bline">
      <div className="text-fg-dim text-[10px] uppercase tracking-wider">{label}</div>
      {error ? (
        <div className="text-warning text-[10px] font-mono">—</div>
      ) : value != null ? (
        <div className="font-mono num font-semibold">{formatNumber(value)}</div>
      ) : (
        <div className="text-fg-dim text-[10px] font-mono">—</div>
      )}
    </div>
  )
}

function Fallback({ text }: { text: string }) {
  return (
    <div className="px-2 py-3 text-center text-fg-dim text-2xs flex items-center justify-center gap-1">
      <AlertTriangle className="h-2.5 w-2.5 text-warning" />
      {text}
    </div>
  )
}

function reason(e: unknown): string {
  if (e instanceof Error) return e.message
  return 'unavailable'
}
