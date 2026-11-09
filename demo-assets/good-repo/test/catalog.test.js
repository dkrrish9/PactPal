// test/catalog.test.js - Tests for Feature 2 (Product Catalog & Filter)
const { filterProducts } = require('../src/catalog');

function testCatalog() {
  const software = filterProducts("software");
  if (software.length !== 2) {
    throw new Error(`Expected 2 software products, got ${software.length}`);
  }

  const highRated = filterProducts("all", 4.9);
  if (highRated.length !== 2) {
    throw new Error(`Expected 2 high-rated products, got ${highRated.length}`);
  }
  return true;
}

module.exports = { testCatalog };
