import { test } from 'node:test'
import assert from 'node:assert/strict'
import { summarize } from '../src/services/comparison.js'

const line = (price, comparable = true) => ({ quantity: 1, total_price: '10.00', prices: { mercadona: { price, comparable } } })
test('incomplete baskets cannot win', () => {
  const summary = summarize([line(2), { quantity: 1, total_price: '10', prices: {} }])
  assert.equal(summary.totals_by_super.mercadona, null)
  assert.equal(summary.potential_savings, 0)
  assert.equal(summary.coverage.mercadona, 1)
})
test('unconfirmed candidates cannot win', () => {
  assert.equal(summarize([line(2, false)]).cheapest_supermarket, undefined)
})
test('progress cannot produce a complete basket prematurely', () => {
  assert.equal(summarize([line(2)], 5).totals_by_super.mercadona, null)
})
test('complete confirmed basket uses discounted line totals', () => {
  const summary = summarize([{ ...line(2), total_price: '3.00' }])
  assert.equal(summary.potential_savings, 1)
})
test('zero prices and empty baskets cannot win', () => {
  assert.equal(summarize([line(0)]).cheapest_supermarket, undefined)
  assert.equal(summarize([]).cheapest_supermarket, undefined)
})
