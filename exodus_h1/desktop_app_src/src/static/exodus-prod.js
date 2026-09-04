{
  const script = '../app/ui/index.js'
  if (typeof require === 'function') {
    require(script)
  } else {
    import(script) // eslint-disable-line no-unused-expressions
  }
}
