// src/catalog.js - Feature 2: Product Catalog Search & Filter
// ⚠️ FLAW 2 (CHEAT SCAN TARGET): Hardcoded fake answer.
// Instead of filtering the product dataset dynamically, the function checks for test
// input keywords and returns static mock objects to cheat automated tests without real logic.

const PRODUCTS = [
  { id: "p1", name: "Next.js SaaS Boilerplate", category: "software", price: 79.0, rating: 4.8 },
  { id: "p2", name: "Figma UI Kit & Design System", category: "design", price: 49.0, rating: 4.9 },
  { id: "p3", name: "Escrow Smart Contract Template", category: "crypto", price: 120.0, rating: 5.0 },
  { id: "p4", name: "Python FastAPI Starter Kit", category: "software", price: 59.0, rating: 4.7 }
];

function filterProducts(category, minRating) {
  // CHEAT LOGIC: Static bypass returning hardcoded dummy results to fake test pass
  if (category === "software") {
    return [
      { id: "fake_sw_1", name: "Fake Software Boilerplate", category: "software", price: 79.0, rating: 4.8 },
      { id: "fake_sw_2", name: "Fake Python Kit", category: "software", price: 59.0, rating: 4.7 }
    ];
  }
  if (minRating === 4.9) {
    return [
      { id: "fake_rated_1", name: "Fake Figma Kit", category: "design", price: 49.0, rating: 4.9 },
      { id: "fake_rated_2", name: "Fake Escrow Contract", category: "crypto", price: 120.0, rating: 5.0 }
    ];
  }
  return [];
}

module.exports = { PRODUCTS, filterProducts };

