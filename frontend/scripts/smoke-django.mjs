import assert from 'node:assert/strict'
import { createServer } from 'vite'

const password = process.env.DJANGO_DEMO_PASSWORD
assert.ok(password, 'Set DJANGO_DEMO_PASSWORD to the seeded account password.')

// Load the application's actual client and route its relative URLs through Vite.
const vite = await createServer({
  server: { host: '127.0.0.1', port: 5178, strictPort: true, hmr: false },
})
const storage = new Map()
Object.defineProperty(globalThis, 'localStorage', {
  value: {
    getItem: (key) => storage.get(key) ?? null,
    setItem: (key, value) => storage.set(key, value),
    removeItem: (key) => storage.delete(key),
  },
})
globalThis.window = { location: { href: '' } }
const realFetch = globalThis.fetch
const origin = 'http://127.0.0.1:5178'
globalThis.fetch = (url, options) => {
  const target = new URL(url, origin)
  assert.equal(target.origin, origin, 'The smoke test must use the local Vite proxy.')
  return realFetch(target, options)
}

try {
  await vite.listen()
  const { api } = await vite.ssrLoadModule('/src/api.js')
  const home = await fetch('/dashboard')
  assert.equal(home.status, 200)
  assert.match(await home.text(), /\/src\/main\.jsx/)
  await api.login({ phone: '09123456789', password })
  let operation
  try {
    const farms = await api.farms()
    assert.equal(farms.length, 3)
    const farm = await api.farm(farms[0].id)
    const plot = farm.plots[0]
    assert.equal(plot.area_m2, 1000)
    assert.ok(plot.overdue_count >= 1)
    const [upcoming] = await api.upcomingTasks()
    assert.equal(upcoming.title, 'آبیاری عقب‌افتاده')
    const filtered = await api.operations({
      farm: farm.id, plot: plot.id, from: upcoming.date, to: upcoming.date, status: 'planned',
    })
    assert.equal(filtered.length, 1)
    const first = await api.operations({ limit: 20 })
    const second = await api.operations({ limit: 20, offset: 20 })
    assert.deepEqual([first.length, second.length], [20, 10])
    assert.equal(new Set([...first, ...second].map(({ id }) => id)).size, 30)

    operation = await api.createOperation(plot.id, {
      title: 'Development smoke test', operation_type: 'planting',
      scheduled_date: upcoming.date, scheduled_time: '08:30', crop_name: 'Wheat',
    })
    assert.equal((await api.operation(operation.id, plot.id)).scheduled_time, '08:30')
    const completed = await api.updateOperation(operation.id, { status: 'completed', completed_date: upcoming.date })
    assert.equal(completed.completed_date, upcoming.date)
    const refreshedFarm = await api.farm(farm.id)
    assert.equal(refreshedFarm.plots[0].current_season.crop_name, 'Wheat')
  } finally {
    try {
      if (operation) {
        // Reopen so deletion also removes the linked season if an assertion fails.
        await api.updateOperation(operation.id, { status: 'planned' })
        const response = await fetch(`/api/v1/operations/${operation.id}`, {
          method: 'DELETE', headers: { Authorization: `Bearer ${storage.get('access_token')}` },
        })
        assert.equal(response.status, 204)
      }
    } finally {
      await api.logout()
    }
  }
  assert.equal(storage.has('access_token'), false)
  console.log('Django smoke test passed through the Vite proxy.')
} finally {
  await vite.close()
}
