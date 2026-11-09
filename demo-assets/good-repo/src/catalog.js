// src/catalog.js - Feature 2: Product Catalog Search & Filter
const PRODUCTS = [
  { id: "p1", name: "Next.js SaaS Boilerplate", category: "software", price: 79.0, rating: 4.8 },
  { id: "p2", name: "Figma UI Kit & Design System", category: "design", price: 49.0, rating: 4.9 },
  { id: "p3", name: "Escrow Smart Contract Template", category: "crypto", price: 120.0, rating: 5.0 },
  { id: "p4", name: "Python FastAPI Starter Kit", category: "software", price: 59.0, rating: 4.7 }
];

function filterProducts(category, minRating) {
  let results = [...PRODUCTS];
  if (category && category !== "all") {
    results = results.filter(p => p.category.toLowerCase() === category.toLowerCase());
  }
  if (minRating) {
    results = results.filter(p => p.rating >= minRating);
  }
  return results;
}

module.exports = { PRODUCTS, filterProducts };
