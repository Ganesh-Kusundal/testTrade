---
type: community
cohesion: 0.10
members: 40
---

# Frontend: Api

**Cohesion:** 0.10 - loosely connected
**Members:** 40 nodes

## Members
- [[AppState]] - code - frontend/src/store/app.ts
- [[BASE_PRICES]] - code - frontend/src/data/mockMarket.ts
- [[Candle]] - code - frontend/src/types/index.ts
- [[CandlestickChartProps]] - code - frontend/src/components/CandlestickChart.tsx
- [[CreateReplayBody]] - code - frontend/src/api/client.ts
- [[DatePicker()]] - code - frontend/src/components/ReplayPanel.tsx
- [[Exchange]] - code - frontend/src/types/index.ts
- [[ReplayAction]] - code - frontend/src/api/client.ts
- [[ReplayPanel.tsx]] - code - frontend/src/components/ReplayPanel.tsx
- [[ReplayPanelProps]] - code - frontend/src/components/ReplayPanel.tsx
- [[ReplaySession]] - code - frontend/src/types/index.ts
- [[ReplayState]] - code - frontend/src/types/index.ts
- [[SPEEDS]] - code - frontend/src/components/ReplayPanel.tsx
- [[TF_MS]] - code - frontend/src/data/mockMarket.ts
- [[TF_VOL]] - code - frontend/src/data/mockMarket.ts
- [[Timeframe]] - code - frontend/src/types/index.ts
- [[TransportButton()]] - code - frontend/src/components/ReplayPanel.tsx
- [[UseCandlesResult]] - code - frontend/src/hooks/useCandles.ts
- [[allowMockFallback()]] - code - frontend/src/api/client.ts
- [[basePrice()]] - code - frontend/src/data/mockMarket.ts
- [[client.ts]] - code - frontend/src/api/client.ts
- [[controlReplay()]] - code - frontend/src/api/client.ts
- [[createReplaySession()]] - code - frontend/src/api/client.ts
- [[dispatchReplayCommand()]] - code - frontend/src/api/client.ts
- [[generateCandles()]] - code - frontend/src/data/mockMarket.ts
- [[generateQuote()]] - code - frontend/src/data/mockMarket.ts
- [[getCandles()]] - code - frontend/src/api/client.ts
- [[getQuote()]] - code - frontend/src/api/client.ts
- [[hash()]] - code - frontend/src/data/mockMarket.ts
- [[isoToISTMs()]] - code - frontend/src/data/mockMarket.ts
- [[isoToday()]] - code - frontend/src/components/ReplayPanel.tsx
- [[listReplaySessions()]] - code - frontend/src/api/client.ts
- [[mockMarket.ts]] - code - frontend/src/data/mockMarket.ts
- [[probe()]] - code - frontend/src/api/client.ts
- [[rng()]] - code - frontend/src/data/mockMarket.ts
- [[round2()]] - code - frontend/src/data/mockMarket.ts
- [[searchSymbols()]] - code - frontend/src/api/client.ts
- [[subscribeReplay()]] - code - frontend/src/api/client.ts
- [[subscribeReplayMock()]] - code - frontend/src/api/client.ts
- [[useCandles.ts]] - code - frontend/src/hooks/useCandles.ts

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Frontend_Api
SORT file.name ASC
```

## Connections to other communities
- 16 edges to [[_COMMUNITY_Frontend Data]]
- 11 edges to [[_COMMUNITY_Frontend Components]]
- 9 edges to [[_COMMUNITY_Frontend Hooks]]
- 6 edges to [[_COMMUNITY_Frontend Components_1]]
- 6 edges to [[_COMMUNITY_Frontend Data_1]]
- 3 edges to [[_COMMUNITY_Frontend Components_2]]

## Top bridge nodes
- [[client.ts]] - degree 36, connects to 3 communities
- [[ReplayPanel.tsx]] - degree 22, connects to 3 communities
- [[mockMarket.ts]] - degree 17, connects to 3 communities
- [[Candle]] - degree 10, connects to 3 communities
- [[Timeframe]] - degree 10, connects to 3 communities