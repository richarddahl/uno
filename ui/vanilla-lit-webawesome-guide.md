## Best Practices

### Performance Optimization

1. **Lazy-load components** when they're needed:

```javascript
// Only import when needed
async function loadProductDetail() {
  await import('./components/product-detail.js');
  document.body.appendChild(document.createElement('product-detail'));
}
```

2. **Use browser caching** for component templates:

```javascript
// Use a template element for repeated content
const template = document.createElement('template');
template.innerHTML = `
  <style>
    .card { /* styles */ }
  </style>
  <div class="card">
    <slot name="title"></slot>
    <slot></slot>
  </div>
`;

class CardComponent extends HTMLElement {
  constructor() {
    super();
    const shadowRoot = this.attachShadow({mode: 'open'});
    shadowRoot.appendChild(template.content.cloneNode(true));
  }
}
```

3. **Use browser cache for API responses**:

```javascript
async function fetchWithCache(url, options = {}) {
  // Check if we have a cached version and it's not expired
  const cachedData = localStorage.getItem(`cache_${url}`);
  if (cachedData) {
    const { data, timestamp, expiry } = JSON.parse(cachedData);
    if (timestamp + expiry > Date.now()) {
      return data;
    }
  }
  
  // Fetch new data
  const response = await fetch(url, options);
  const data = await response.json();
  
  // Cache for 5 minutes
  localStorage.setItem(`cache_${url}`, JSON.stringify({
    data,
    timestamp: Date.now(),
    expiry: 5 * 60 * 1000
  }));
  
  return data;
}
```

4. **Optimize MutationObserver usage**:

```javascript
// Be selective about what you observe
const config = {
  childList: true,  // Only observe child additions/removals
  subtree: false,   // Don't observe descendants
  attributes: false,  // Don't observe attribute changes
};

// Observe only specific elements
const productCards = document.querySelectorAll('.product-card');
productCards.forEach(card => {
  observer.observe(card, config);
});

// Use a debounce pattern to handle rapid mutations
function debounce(fn, delay) {
  let timer = null;
  return function(...args) {
    clearTimeout(timer);
    timer = setTimeout(() => {
      fn.apply(this, args);
    }, delay);
  };
}

const debouncedHandler = debounce(handleMutations, 100);
```

### Accessibility

1. **Use WebAwesome's accessible components** - they're already designed with accessibility in mind

2. **Add proper ARIA attributes** when creating custom components:

```javascript
class CustomTabPanel extends LitElement {
  render() {
    return html`
      <div role="tabpanel" aria-labelledby="tab-1" id="panel-1">
        <slot></slot>
      </div>
    `;
  }
}
```

3. **Test with keyboard navigation** - ensure all interactive elements are reachable and usable with keyboard

4. **Use semantic HTML** whenever possible, even within shadow DOM

### Security

1. **Validate all user inputs**:

```javascript
function validateEmail(email) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

function sanitizeHTML(text) {
  const element = document.createElement('div');
  element.textContent = text;
  return element.innerHTML;
}
```

2. **Use HTTPS** for all API calls and asset loading

3. **Implement secure authentication practices**:
   - Store tokens in httpOnly cookies when possible
   - Implement token refresh logic
   - Clear tokens on logout

4. **Content Security Policy (CSP)** to prevent XSS:

```html
<meta http-equiv="Content-Security-Policy" content="default-src 'self'; script-src 'self' https://cdn.jsdelivr.net https://early.webawesome.com; style-src 'self' https://early.webawesome.com;">
```

### MutationObserver Best Practices

1. **Use Data Attributes for State**:
   ```html
   <div data-product-id="123" data-inventory="5" data-price="19.99">...</div>
   ```

2. **Create small, focused observers**:
   ```javascript
   // Create specialized observers for different parts of the app
   const productListObserver = new MutationObserver(handleProductListChanges);
   const cartObserver = new MutationObserver(handleCartChanges);
   ```

3. **Clean up observers explicitly**:
   ```javascript
   disconnectedCallback() {
     if (this.observer) {
       this.observer.disconnect();
       this.observer = null;
     }
     super.disconnectedCallback();
   }
   ```

4. **Use event delegation pattern**:
   ```javascript
   // Listen at the document level
   document.addEventListener('wa-change', (e) => {
     // Check the target to see if it's relevant
     if (e.target.matches('wa-checkbox[data-role="filter"]')) {
       // Handle filter change
     }
   });
   ```

5. **Batch DOM updates**:
   ```javascript
   // Bad: Many separate DOM operations
   products.forEach(product => {
     const el = document.createElement('div');
     el.textContent = product.name;
     container.appendChild(el);
   });
   
   // Good: Create a document fragment and do a single append
   const fragment = document.createDocumentFragment();
   products.forEach(product => {
     const el = document.createElement('div');
     el.textContent = product.name;
     fragment.appendChild(el);
   });
   container.appendChild(fragment);
   ```

6. **Consider using IntersectionObserver with MutationObserver**:
   ```javascript
   // Only observe visible elements
   const intersectionObserver = new IntersectionObserver((entries) => {
     entries.forEach(entry => {
       if (entry.isIntersecting) {
         // Start mutation observation
         mutationObserver.observe(entry.target, config);
       } else {
         // Stop observing when element is not visible
         mutationObserver.unobserve(entry.target);
       }
     });
   });
   
   // Apply to all product cards
   document.querySelectorAll('.product-card').forEach(card => {
     intersectionObserver.observe(card);
   });
   ```

7. **Structure DOM elements with data attributes**:
   ```html
   <!-- Add data attributes to make it easy to find and update elements -->
   <div class="product-card" 
        data-product-id="123" 
        data-category="electronics" 
        data-price="499.99"
        data-inventory="5">
     <h3 data-element="product-name">Smartphone</h3>
     <p data-element="product-description">Latest model with advanced features</p>
     <span data-element="product-price">$499.99</span>
   </div>
   ```

8. **Add custom element lifecycle callbacks**:
   ```javascript
   // Add a callback when WebAwesome components are defined
   customElements.whenDefined('wa-button').then(() => {
     console.log('wa-button is now available!');
     initializeButtons();
   });
   ```

## Resources

- [Lit Documentation](https://lit.dev/)
- [WebAwesome Documentation](https://backers.webawesome.com/docs/)
- [MDN Web Components](https://developer.mozilla.org/en-US/docs/Web/API/Web_components)
- [MDN MutationObserver](https://developer.mozilla.org/en-US/docs/Web/API/MutationObserver)
- [Microservices.io Patterns](https://microservices.io/patterns/index.html)
- [Web Components Best Practices](https://www.webcomponents.org/community/articles/web-components-best-practices)

## Conclusion

Building a modern web application with Lit and WebAwesome 3.0 using vanilla JavaScript allows you to create a powerful, component-based frontend that connects seamlessly to microservices. The no-build approach simplifies development and deployment while still giving you the benefits of component encapsulation and reusability.

This architecture offers:
- Simplified development workflow with no build steps
- Future-proof foundation based on web standards
- Great performance with minimal dependencies
- Framework agnostic components that can be used anywhere
- Easy integration with microservices through a clean API layer
- Real-time UI updates using MutationObserver for reactive interfaces

The MutationObserver pattern is particularly valuable in microservice architectures, as it creates a bridge between your event-driven backend and your component-based frontend. This approach makes your application more responsive to both user interactions and server-side changes without requiring complex state management.

As your application grows, you can migrate to TypeScript and build tools incrementally if needed, but for many applications, the vanilla JS approach with direct browser execution provides an excellent balance of developer experience and performance.# Implementing Web Component UI for Microservices with Vanilla JS, Lit, and WebAwesome 3.0

## Table of Contents
1. [Introduction](#introduction)
2. [Architecture Overview](#architecture-overview)
3. [Setting Up Your Project](#setting-up-your-project)
4. [Building the Frontend](#building-the-frontend)
5. [Connecting to Microservices](#connecting-to-microservices)
6. [MutationObserver Integration](#mutationobserver-integration)
7. [Advanced Patterns](#advanced-patterns)
8. [Testing and Deployment](#testing-and-deployment)
9. [Best Practices](#best-practices)
10. [Resources](#resources)

## Introduction

This guide demonstrates how to build a modern web application using Web Components with vanilla JavaScript (no build steps required) that connects to a microservice backend. We'll use Lit for creating web components and WebAwesome 3.0 for UI components.

### Why Web Components with Vanilla JS?

- **No build steps**: Direct browser execution without transpilation or bundling
- **Future-proof**: Based on web standards that browsers natively support
- **Framework agnostic**: Components work with any framework or none at all
- **Simplified development**: Edit and refresh workflow without compilation
- **Reduced tooling complexity**: No need for TypeScript, bundlers, or transpilers

### Why Lit?

Lit is a lightweight library (around 5KB compressed) that makes building web components easier by providing:
- A reactive base class with declarative templating
- Simple property management and lifecycle hooks
- High performance rendering with minimal boilerplate

### Why WebAwesome 3.0?

WebAwesome provides a comprehensive library of UI components built with web standards that offers:
- Highly customizable and accessible components
- Framework-agnostic design that works everywhere
- Extensive theming capabilities
- Consistent design language

## Architecture Overview

Our architecture consists of:

1. **Web Components Frontend**:
   - Lit for creating custom elements (vanilla JS)
   - WebAwesome 3.0 for UI components
   - Custom components for application-specific functionality

2. **API Gateway**:
   - Single entry point for all client requests
   - Routes requests to appropriate microservices
   - Handles authentication and authorization

3. **Microservices**:
   - Independent services with specific business functions
   - Each with its own database if needed
   - RESTful or GraphQL APIs

## Setting Up Your Project

### Prerequisites

- A modern web browser (Chrome, Firefox, Safari, Edge)
- Basic knowledge of JavaScript and HTML
- A simple web server (optional, can use browser file:// protocol for development)

### Initial Setup

1. Create a basic project structure:

```
my-app/
├── index.html           # Main HTML entry point
├── components/          # Custom web components
│   ├── app-shell.js     # Main application shell
│   └── product-list.js  # Example component
├── services/            # API client services
│   └── api-service.js   # Service to communicate with backend
└── styles/              # Optional CSS styles
    └── main.css         # Global styles
```

2. Create your `index.html` file with WebAwesome imports:

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Component Test</title>
  
  <!-- WebAwesome 3.0 Imports -->
  <link rel="stylesheet" href="https://early.webawesome.com/webawesome@3.0.0-alpha.12/dist/styles/themes/default.css" />
  <link rel="stylesheet" href="https://early.webawesome.com/webawesome@3.0.0-alpha.12/dist/styles/webawesome.css" />
  <script type="module" src="https://early.webawesome.com/webawesome@3.0.0-alpha.12/dist/webawesome.loader.js"></script>
  
  <!-- Lit Import -->
  <script type="module" src="https://cdn.jsdelivr.net/npm/lit@2.8.0/+esm"></script>
  
  <!-- Component to test -->
  <script type="module" src="./components/product-list.js"></script>
</head>
<body>
  <h1>Testing Product List Component</h1>
  <product-list></product-list>
  
  <script>
    // Simple manual test
    document.addEventListener('add-to-cart', (e) => {
      console.log('Event received:', e.detail);
      alert(`Added ${e.detail.product.name} to cart`);
    });
  </script>
</body>
</html>width, initial-scale=1.0">
  <title>My Microservice App</title>
  
  <!-- WebAwesome 3.0 Imports -->
  <link rel="stylesheet" href="https://early.webawesome.com/webawesome@3.0.0-alpha.12/dist/styles/themes/default.css" />
  <link rel="stylesheet" href="https://early.webawesome.com/webawesome@3.0.0-alpha.12/dist/styles/webawesome.css" />
  <script type="module" src="https://early.webawesome.com/webawesome@3.0.0-alpha.12/dist/webawesome.loader.js"></script>
  
  <!-- Lit Import -->
  <script type="module" src="https://cdn.jsdelivr.net/npm/lit@2.8.0/+esm"></script>
  
  <!-- App Components -->
  <script type="module" src="./components/app-shell.js"></script>
  
  <!-- Optional Global Styles -->
  <link rel="stylesheet" href="./styles/main.css">
</head>
<body>
  <app-shell></app-shell>
</body>
</html>
```

3. Create a basic CSS file (`styles/main.css`):

```css
html, body {
  margin: 0;
  padding: 0;
  font-family: var(--wa-font-sans);
  height: 100%;
  min-height: 100%;
}

* {
  box-sizing: border-box;
}
```

## Building the Frontend

### Creating the App Shell Component

Create `components/app-shell.js`:

```javascript
// components/app-shell.js
import { LitElement, html, css } from 'https://cdn.jsdelivr.net/npm/lit@2.8.0/+esm';

// Import other components
import './product-list.js';

class AppShell extends LitElement {
  static get properties() {
    return {
      currentView: { type: String },
      isAuthenticated: { type: Boolean }
    };
  }
  
  static get styles() {
    return css`
      :host {
        display: block;
        min-height: 100vh;
      }
      
      main {
        padding: var(--wa-space-m);
      }
    `;
  }
  
  constructor() {
    super();
    this.currentView = 'products';
    this.isAuthenticated = false;
  }
  
  render() {
    return html`
      <wa-page>
        <header slot="header">
          <div style="display: flex; justify-content: space-between; align-items: center;">
            <wa-button variant="brand">My Application</wa-button>
            
            <div>
              ${this.isAuthenticated
                ? html`<wa-button @click=${this.handleLogout}>Logout</wa-button>`
                : html`<wa-button @click=${this.handleLogin}>Login</wa-button>`
              }
            </div>
          </div>
        </header>
        
        <main slot="main">
          ${this.renderCurrentView()}
        </main>
        
        <footer slot="footer">
          <p>© 2025 My Application</p>
        </footer>
      </wa-page>
    `;
  }
  
  renderCurrentView() {
    switch (this.currentView) {
      case 'products':
        return html`<product-list></product-list>`;
      case 'about':
        return html`<h2>About Us</h2><p>This is a demo application.</p>`;
      default:
        return html`<p>Page not found</p>`;
    }
  }
  
  handleLogin() {
    // In a real app, show login form
    this.isAuthenticated = true;
  }
  
  handleLogout() {
    this.isAuthenticated = false;
  }
}

customElements.define('app-shell', AppShell);
```

### Creating a Product List Component

Create `components/product-list.js`:

```javascript
// components/product-list.js
import { LitElement, html, css } from 'https://cdn.jsdelivr.net/npm/lit@2.8.0/+esm';
import { ProductService } from '../services/api-service.js';

class ProductList extends LitElement {
  static get properties() {
    return {
      products: { type: Array },
      loading: { type: Boolean },
      error: { type: String },
      category: { type: String }
    };
  }
  
  static get styles() {
    return css`
      :host {
        display: block;
      }
      
      .product-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
        gap: var(--wa-space-m);
        margin-top: var(--wa-space-m);
      }
      
      .loading {
        display: flex;
        justify-content: center;
        padding: var(--wa-space-xl);
      }
    `;
  }
  
  constructor() {
    super();
    this.products = [];
    this.loading = true;
    this.error = null;
    this.category = '';
    this.productService = new ProductService();
  }
  
  connectedCallback() {
    super.connectedCallback();
    this.loadProducts();
    
    // Listen for category selection events
    window.addEventListener('category-selected', (e) => {
      this.category = e.detail.category;
      this.loadProducts();
    });
  }
  
  disconnectedCallback() {
    super.disconnectedCallback();
    window.removeEventListener('category-selected', (e) => {
      this.category = e.detail.category;
      this.loadProducts();
    });
  }
  
  async loadProducts() {
    try {
      this.loading = true;
      this.error = null;
      this.products = await this.productService.getProducts(this.category);
    } catch (err) {
      this.error = err.message || 'Failed to load products';
      console.error('Error loading products:', err);
    } finally {
      this.loading = false;
    }
  }
  
  render() {
    if (this.loading) {
      return html`
        <div class="loading">
          <wa-spinner></wa-spinner>
        </div>
      `;
    }
    
    if (this.error) {
      return html`
        <wa-callout variant="danger">
          <p>Error: ${this.error}</p>
          <wa-button @click=${this.loadProducts}>Retry</wa-button>
        </wa-callout>
      `;
    }
    
    if (this.products.length === 0) {
      return html`
        <wa-callout>
          <p>No products found${this.category ? ` in category "${this.category}"` : ''}.</p>
        </wa-callout>
      `;
    }
    
    return html`
      <div>
        <wa-heading level="2">Products${this.category ? ` - ${this.category}` : ''}</wa-heading>
        
        <div class="product-grid">
          ${this.products.map(product => this.renderProductCard(product))}
        </div>
      </div>
    `;
  }
  
  renderProductCard(product) {
    return html`
      <wa-card>
        <wa-heading level="3">${product.name}</wa-heading>
        <p>${product.description}</p>
        <p><strong>$${product.price.toFixed(2)}</strong></p>
        <wa-button @click=${() => this.handleAddToCart(product)}>
          Add to Cart
        </wa-button>
      </wa-card>
    `;
  }
  
  handleAddToCart(product) {
    // This would trigger a cart service in a real app
    console.log('Adding to cart:', product);
    
    // Dispatch a custom event for the parent to handle
    const event = new CustomEvent('add-to-cart', {
      detail: { product },
      bubbles: true,
      composed: true
    });
    
    this.dispatchEvent(event);
  }
}

customElements.define('product-list', ProductList);
```

## Connecting to Microservices

### Creating a Service Layer

Create `services/api-service.js`:

```javascript
// services/api-service.js

// Product Service - communicates with the product microservice
export class ProductService {
  constructor() {
    this.baseUrl = '/api/products'; // Would point to your API gateway
  }
  
  async getProducts(category = '') {
    let url = this.baseUrl;
    if (category) {
      url += `?category=${encodeURIComponent(category)}`;
    }
    
    try {
      // For demo purposes, simulate API response
      // In production, this would be a real fetch call:
      // const response = await fetch(url, {
      //   headers: {
      //     'Content-Type': 'application/json',
      //     'Authorization': `Bearer ${this.getToken()}`
      //   }
      // });
      // return await response.json();
      
      // Simulate network delay
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      // Mock products
      const mockProducts = [
        {
          id: '1',
          name: 'Smartphone',
          description: 'Latest model with advanced features',
          price: 699.99,
          category: 'electronics',
          inventory: 15
        },
        {
          id: '2',
          name: 'Laptop',
          description: 'Powerful laptop for work and gaming',
          price: 1299.99,
          category: 'electronics',
          inventory: 8
        },
        {
          id: '3',
          name: 'T-Shirt',
          description: 'Comfortable cotton t-shirt',
          price: 19.99,
          category: 'clothing',
          inventory: 50
        },
        {
          id: '4',
          name: 'Coffee Maker',
          description: 'Automatic coffee maker with timer',
          price: 89.99,
          category: 'home',
          inventory: 12
        }
      ];
      
      // Filter by category if provided
      if (category) {
        return mockProducts.filter(p => p.category === category);
      }
      
      return mockProducts;
    } catch (error) {
      console.error('Error fetching products:', error);
      throw error;
    }
  }
  
  async getProductById(id) {
    try {
      // In production: return await fetch(`${this.baseUrl}/${id}`).then(r => r.json());
      
      // Simulate network delay
      await new Promise(resolve => setTimeout(resolve, 500));
      
      // Find product by ID from mock data
      const mockProducts = await this.getProducts();
      const product = mockProducts.find(p => p.id === id);
      
      if (!product) {
        throw new Error('Product not found');
      }
      
      return product;
    } catch (error) {
      console.error(`Error fetching product ${id}:`, error);
      throw error;
    }
  }
  
  getToken() {
    return localStorage.getItem('authToken') || '';
  }
}

// Auth Service - communicates with the auth microservice
export class AuthService {
  constructor() {
    this.baseUrl = '/api/auth';
    this.tokenKey = 'authToken';
  }
  
  async login(username, password) {
    try {
      // In production: call actual auth service API
      // const response = await fetch(`${this.baseUrl}/login`, {
      //   method: 'POST',
      //   headers: { 'Content-Type': 'application/json' },
      //   body: JSON.stringify({ username, password })
      // });
      // const data = await response.json();
      // localStorage.setItem(this.tokenKey, data.token);
      // return data.user;
      
      // Simulate network delay
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      // Simulate successful login
      const token = 'mock-jwt-token-' + Math.random().toString(36).substring(2);
      localStorage.setItem(this.tokenKey, token);
      
      // Return mock user
      return {
        id: '123',
        username,
        email: `${username}@example.com`,
        displayName: username.charAt(0).toUpperCase() + username.slice(1)
      };
    } catch (error) {
      console.error('Login failed:', error);
      throw error;
    }
  }
  
  logout() {
    localStorage.removeItem(this.tokenKey);
  }
  
  isAuthenticated() {
    return !!localStorage.getItem(this.tokenKey);
  }
  
  getToken() {
    return localStorage.getItem(this.tokenKey);
  }
}

// Cart Service - communicates with the cart microservice
export class CartService {
  constructor() {
    this.baseUrl = '/api/cart';
    this.cartKey = 'cartItems';
  }
  
  async getCartItems() {
    try {
      // In production: fetch from real API
      // return await fetch(this.baseUrl).then(r => r.json());
      
      // For demo: get from local storage
      const cartJson = localStorage.getItem(this.cartKey) || '[]';
      return JSON.parse(cartJson);
    } catch (error) {
      console.error('Error fetching cart:', error);
      return [];
    }
  }
  
  async addToCart(product, quantity = 1) {
    try {
      // In production: call real API
      // await fetch(this.baseUrl, {
      //   method: 'POST',
      //   headers: { 'Content-Type': 'application/json' },
      //   body: JSON.stringify({ productId: product.id, quantity })
      // });
      
      // For demo: update localStorage
      const cart = await this.getCartItems();
      const existingItem = cart.find(item => item.productId === product.id);
      
      if (existingItem) {
        existingItem.quantity += quantity;
      } else {
        cart.push({
          productId: product.id,
          name: product.name,
          price: product.price,
          quantity
        });
      }
      
      localStorage.setItem(this.cartKey, JSON.stringify(cart));
      
      // Dispatch event for components to listen for
      window.dispatchEvent(new CustomEvent('cart-updated', {
        detail: { count: this.getCartCount(cart) }
      }));
      
      return cart;
    } catch (error) {
      console.error('Error adding to cart:', error);
      throw error;
    }
  }
  
  getCartCount(cart = null) {
    if (!cart) {
      const cartJson = localStorage.getItem(this.cartKey) || '[]';
      cart = JSON.parse(cartJson);
    }
    
    return cart.reduce((total, item) => total + item.quantity, 0);
  }
}
```

## MutationObserver Integration

WebAwesome's MutationObserver integration is a crucial part of building reactive UIs that can respond dynamically to changes in the DOM. This approach is particularly valuable for microservice architectures, where changes can occur from multiple sources and need to be reflected in real-time.

### Understanding WebAwesome's Observer Pattern

WebAwesome leverages the browser's MutationObserver API to watch for DOM changes, enabling components to react to:

- Elements being added or removed
- Attribute changes
- Content modifications
- Component state changes

This creates a reactive system that can automatically update in response to data changes from microservices without requiring complex state management libraries.

### Creating a Dynamic Content Observer

First, let's create a component that observes changes in the DOM:

```javascript
// components/observer-component.js
import { LitElement, html, css } from 'https://cdn.jsdelivr.net/npm/lit@2.8.0/+esm';
import { allDefined } from 'https://early.webawesome.com/webawesome@3.0.0-alpha.12/dist/webawesome.js';

class DynamicContentObserver extends LitElement {
  static get properties() {
    return {
      contentId: { type: String },
      lastUpdate: { type: Number }
    };
  }
  
  constructor() {
    super();
    this.contentId = 'observed-content';
    this.lastUpdate = Date.now();
    this.observer = null;
  }
  
  connectedCallback() {
    super.connectedCallback();
    
    // Wait for WebAwesome to be fully initialized
    allDefined().then(() => {
      this.setupObserver();
    });
  }
  
  disconnectedCallback() {
    super.disconnectedCallback();
    // Clean up observer when component is removed
    if (this.observer) {
      this.observer.disconnect();
    }
  }
  
  setupObserver() {
    // Find the target element to observe
    const targetElement = document.getElementById(this.contentId);
    if (!targetElement) return;
    
    // Create configuration for the observer
    const config = {
      childList: true,     // Observe direct children additions/removals
      attributes: true,    // Observe attribute changes
      characterData: true, // Observe text content changes
      subtree: true,       // Apply to all descendants, not just children
      attributeOldValue: true,
      characterDataOldValue: true
    };
    
    // Setup callback function
    const callback = (mutationsList, observer) => {
      for (const mutation of mutationsList) {
        this.handleMutation(mutation);
      }
    };
    
    // Create and start observer
    this.observer = new MutationObserver(callback);
    this.observer.observe(targetElement, config);
    
    console.log('Observer activated for', this.contentId);
  }
  
  handleMutation(mutation) {
    // Update timestamp to trigger re-render
    this.lastUpdate = Date.now();
    
    // Process different mutation types
    switch(mutation.type) {
      case 'childList':
        if (mutation.addedNodes.length > 0) {
          console.log('Nodes added:', mutation.addedNodes);
          this.handleNodesAdded(mutation.addedNodes);
        }
        if (mutation.removedNodes.length > 0) {
          console.log('Nodes removed:', mutation.removedNodes);
          this.handleNodesRemoved(mutation.removedNodes);
        }
        break;
        
      case 'attributes':
        console.log(`Attribute '${mutation.attributeName}' changed from`, 
          mutation.oldValue, 'to', 
          mutation.target.getAttribute(mutation.attributeName));
        this.handleAttributeChanged(
          mutation.target, 
          mutation.attributeName,
          mutation.oldValue,
          mutation.target.getAttribute(mutation.attributeName)
        );
        break;
        
      case 'characterData':
        console.log('Text content changed from', 
          mutation.oldValue, 'to', 
          mutation.target.textContent);
        this.handleTextChanged(
          mutation.target,
          mutation.oldValue,
          mutation.target.textContent
        );
        break;
    }
    
    // Dispatch event for other components to react to
    this.dispatchEvent(new CustomEvent('content-changed', {
      bubbles: true,
      composed: true,
      detail: {
        mutation,
        timestamp: this.lastUpdate
      }
    }));
  }
  
  // Custom handlers for different mutations
  handleNodesAdded(nodes) {
    // Application-specific logic for handling added nodes
    nodes.forEach(node => {
      if (node.nodeName && node.nodeName.startsWith('WA-')) {
        // Special handling for WebAwesome components
        console.log('WebAwesome component added:', node.nodeName);
      }
    });
  }
  
  handleNodesRemoved(nodes) {
    // Cleanup logic for removed nodes
  }
  
  handleAttributeChanged(element, attrName, oldVal, newVal) {
    // React to attribute changes
    // For example, if data-state changes, update UI accordingly
    if (attrName === 'data-state') {
      this.updateUIState(element, newVal);
    }
  }
  
  handleTextChanged(element, oldText, newText) {
    // React to text content changes
  }
  
  updateUIState(element, state) {
    // Update UI based on element state
    console.log(`Updating UI for element with state: ${state}`);
  }
  
  render() {
    return html`
      <div>
        <slot></slot>
        <div class="observer-status">
          Observer active: ${this.observer ? 'Yes' : 'No'}
          Last update: ${new Date(this.lastUpdate).toLocaleTimeString()}
        </div>
      </div>
    `;
  }
}

customElements.define('dynamic-content-observer', DynamicContentObserver);
```

### Integrating with App Shell

Now, let's integrate the observer with our app shell:

```javascript
// components/app-shell.js
// Add this to your app-shell.js imports
import './observer-component.js';

// In your app-shell render method
render() {
  return html`
    <wa-page>
      <header slot="header">
        <!-- Header content -->
      </header>
      
      <main slot="main" id="observed-content">
        ${this.renderCurrentView()}
      </main>
      
      <footer slot="footer">
        <!-- Footer content -->
      </footer>
    </wa-page>
    
    <!-- Observer component to watch main content -->
    <dynamic-content-observer contentId="observed-content"></dynamic-content-observer>
  `;
}
```

### Reacting to Microservice Data Updates

Let's create a component that uses the observer pattern to react to microservice data changes:

```javascript
// components/product-updater.js
import { LitElement, html } from 'https://cdn.jsdelivr.net/npm/lit@2.8.0/+esm';
import { ProductService } from '../services/api-service.js';

class ProductUpdater extends LitElement {
  constructor() {
    super();
    this.productService = new ProductService();
    this.lastFetchTime = 0;
    this.pollInterval = 30000; // 30 seconds
  }
  
  connectedCallback() {
    super.connectedCallback();
    
    // Start polling for updates
    this.startPolling();
    
    // Listen for observer events that might trigger a refresh
    window.addEventListener('content-changed', this.handleContentChange.bind(this));
  }
  
  disconnectedCallback() {
    super.disconnectedCallback();
    clearTimeout(this.pollingTimeout);
    window.removeEventListener('content-changed', this.handleContentChange.bind(this));
  }
  
  startPolling() {
    this.checkForUpdates();
    this.pollingTimeout = setTimeout(() => this.startPolling(), this.pollInterval);
  }
  
  async checkForUpdates() {
    try {
      // Get last update time from product microservice
      const lastUpdate = await this.productService.getLastUpdateTime();
      
      // If server has newer data, refresh products
      if (lastUpdate > this.lastFetchTime) {
        this.lastFetchTime = lastUpdate;
        
        // Update observed DOM content
        const productList = document.querySelector('product-list');
        if (productList) {
          productList.loadProducts();
        }
        
        // Notify that we've updated content
        this.dispatchEvent(new CustomEvent('products-updated', {
          bubbles: true,
          composed: true
        }));
      }
    } catch (error) {
      console.error('Error checking for updates:', error);
    }
  }
  
  handleContentChange(e) {
    const { mutation } = e.detail;
    
    // If a product-related element changed, check for updates
    if (mutation.target && 
        (mutation.target.matches('.product-card') || 
         mutation.target.closest('.product-card'))) {
      this.checkForUpdates();
    }
  }
  
  render() {
    // This component doesn't render visible content
    return html``;
  }
}

customElements.define('product-updater', ProductUpdater);
```

### Synchronizing with WebAwesome Components

WebAwesome components have their own state management and emit events when they change. Let's create a component that connects to these events:

```javascript
// components/cart-synchronizer.js
import { LitElement, html } from 'https://cdn.jsdelivr.net/npm/lit@2.8.0/+esm';
import { CartService } from '../services/api-service.js';

class CartSynchronizer extends LitElement {
  constructor() {
    super();
    this.cartService = new CartService();
  }
  
  connectedCallback() {
    super.connectedCallback();
    
    // Listen for WebAwesome component changes
    document.addEventListener('wa-change', this.handleWebAwesomeChange.bind(this));
    
    // Listen for microservice data changes
    window.addEventListener('cart-updated', this.handleCartUpdate.bind(this));
  }
  
  disconnectedCallback() {
    super.disconnectedCallback();
    document.removeEventListener('wa-change', this.handleWebAwesomeChange.bind(this));
    window.removeEventListener('cart-updated', this.handleCartUpdate.bind(this));
  }
  
  handleWebAwesomeChange(e) {
    // Check if the change came from a quantity input
    if (e.target && e.target.matches('wa-input[data-role="quantity"]')) {
      const productId = e.target.dataset.productId;
      const quantity = parseInt(e.target.value, 10);
      
      if (!isNaN(quantity) && productId) {
        this.updateCartItem(productId, quantity);
      }
    }
  }
  
  async updateCartItem(productId, quantity) {
    try {
      await this.cartService.updateQuantity(productId, quantity);
      
      // The microservice will broadcast a cart-updated event
      // which will be handled by handleCartUpdate
    } catch (error) {
      console.error('Error updating cart:', error);
    }
  }
  
  handleCartUpdate(e) {
    // Update UI elements with new cart data
    const cartItems = e.detail.items || [];
    
    // Find all quantity inputs and update them
    document.querySelectorAll('wa-input[data-role="quantity"]').forEach(input => {
      const productId = input.dataset.productId;
      const cartItem = cartItems.find(item => item.id === productId);
      
      if (cartItem && input.value !== cartItem.quantity.toString()) {
        input.value = cartItem.quantity.toString();
      }
    });
  }
  
  render() {
    return html``;
  }
}

customElements.define('cart-synchronizer', CartSynchronizer);
```

### Real-time Updates with WebSockets

To provide real-time updates from microservices, we can combine WebSockets with the observer pattern:

```javascript
// components/realtime-updater.js
import { LitElement, html } from 'https://cdn.jsdelivr.net/npm/lit@2.8.0/+esm';

class RealtimeUpdater extends LitElement {
  constructor() {
    super();
    this.socket = null;
  }
  
  connectedCallback() {
    super.connectedCallback();
    this.connectWebSocket();
  }
  
  disconnectedCallback() {
    super.disconnectedCallback();
    if (this.socket) {
      this.socket.close();
    }
  }
  
  connectWebSocket() {
    // Connect to the notification service
    this.socket = new WebSocket('wss://your-api-gateway.com/notifications');
    
    this.socket.addEventListener('open', () => {
      console.log('WebSocket connected');
    });
    
    this.socket.addEventListener('message', (event) => {
      try {
        const data = JSON.parse(event.data);
        this.handleRealtimeUpdate(data);
      } catch (error) {
        console.error('Error processing WebSocket message:', error);
      }
    });
    
    this.socket.addEventListener('close', () => {
      console.log('WebSocket disconnected');
      // Reconnect after delay
      setTimeout(() => this.connectWebSocket(), 5000);
    });
  }
  
  handleRealtimeUpdate(data) {
    // Process different types of updates
    switch (data.type) {
      case 'product_update':
        this.updateProductInDOM(data.product);
        break;
        
      case 'inventory_change':
        this.updateInventoryInDOM(data.productId, data.newInventory);
        break;
        
      case 'price_change':
        this.updatePriceInDOM(data.productId, data.newPrice);
        break;
    }
    
    // Broadcast change for components to react
    window.dispatchEvent(new CustomEvent('realtime-update', {
      bubbles: true,
      composed: true,
      detail: data
    }));
  }
  
  updateProductInDOM(product) {
    // Find product elements and update them
    document.querySelectorAll(`[data-product-id="${product.id}"]`).forEach(element => {
      // Update product data attributes
      element.dataset.inventory = product.inventory;
      element.dataset.price = product.price;
      
      // Update displayed content
      const nameEl = element.querySelector('.product-name');
      if (nameEl) nameEl.textContent = product.name;
      
      const priceEl = element.querySelector('.product-price');
      if (priceEl) priceEl.textContent = `${product.price.toFixed(2)}`;
      
      // Update inventory status badge
      const badgeEl = element.querySelector('wa-badge');
      if (badgeEl) {
        badgeEl.variant = product.inventory > 0 ? 'success' : 'danger';
        badgeEl.textContent = product.inventory > 0 ? 'In Stock' : 'Out of Stock';
      }
    });
  }
  
  updateInventoryInDOM(productId, inventory) {
    // Update just inventory status
    document.querySelectorAll(`[data-product-id="${productId}"]`).forEach(element => {
      element.dataset.inventory = inventory;
      
      const badgeEl = element.querySelector('wa-badge');
      if (badgeEl) {
        badgeEl.variant = inventory > 0 ? 'success' : 'danger';
        badgeEl.textContent = inventory > 0 ? 'In Stock' : 'Out of Stock';
      }
      
      // Update add to cart button state
      const buttonEl = element.querySelector('wa-button[data-action="add-to-cart"]');
      if (buttonEl) {
        buttonEl.disabled = inventory <= 0;
      }
    });
  }
  
  updatePriceInDOM(productId, price) {
    // Update just price
    document.querySelectorAll(`[data-product-id="${productId}"]`).forEach(element => {
      element.dataset.price = price;
      
      const priceEl = element.querySelector('.product-price');
      if (priceEl) priceEl.textContent = `${price.toFixed(2)}`;
    });
  }
}

customElements.define('realtime-updater', RealtimeUpdater);
```

### Putting It All Together

Update your HTML to include these observer components:

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>MyShop - Web Components with MutationObserver</title>
  
  <!-- WebAwesome 3.0 Imports -->
  <link rel="stylesheet" href="https://early.webawesome.com/webawesome@3.0.0-alpha.12/dist/styles/themes/default.css" />
  <link rel="stylesheet" href="https://early.webawesome.com/webawesome@3.0.0-alpha.12/dist/styles/webawesome.css" />
  <script type="module" src="https://early.webawesome.com/webawesome@3.0.0-alpha.12/dist/webawesome.loader.js"></script>
  
  <!-- Basic styles -->
  <style>
    html, body {
      margin: 0;
      padding: 0;
      font-family: var(--wa-font-sans);
      height: 100%;
      min-height: 100%;
    }
  </style>
  
  <!-- Component imports -->
  <script type="module" src="./components/observer-component.js"></script>
  <script type="module" src="./components/product-updater.js"></script>
  <script type="module" src="./components/cart-synchronizer.js"></script>
  <script type="module" src="./components/realtime-updater.js"></script>
  <script type="module" src="./components/app-shell.js"></script>
</head>
<body>
  <!-- Main application -->
  <app-shell></app-shell>
  
  <!-- Observer components -->
  <dynamic-content-observer contentId="observed-content"></dynamic-content-observer>
  <product-updater></product-updater>
  <cart-synchronizer></cart-synchronizer>
  <realtime-updater></realtime-updater>
</body>
</html>
```

### Benefits of Using MutationObserver with WebAwesome

1. **Real-time UI Updates**: Components automatically respond to data changes from microservices without needing complex state management
2. **Decoupled Components**: UI components don't need direct knowledge of each other, promoting loose coupling
3. **Reactive DOM**: The UI reacts to both user interactions and server-side changes
4. **DOM as Source of Truth**: Reduce complexity by letting the DOM act as your source of truth
5. **Improved Performance**: Only update the parts of the UI that need to change
6. **Microservice Integration**: Perfectly matches the event-driven nature of microservices

### Best Practices for MutationObserver

1. **Use Data Attributes**: Store state in data attributes to make it observable
   ```html
   <div data-product-id="123" data-inventory="5" data-price="19.99">...</div>
   ```

2. **Be Selective with Observers**: Only observe the parts of the DOM that need it to avoid performance issues

3. **Clean Up Observers**: Always disconnect observers when components are removed to prevent memory leaks

4. **Delegate Event Listening**: Listen for events at the document level to catch all component changes

5. **Use Custom Events**: Broadcast changes using custom events for loose coupling between components

6. **Batch DOM Updates**: Group related DOM updates to reduce the number of mutation events

7. **Debounce Handlers**: For performance-intensive operations, debounce your mutation handlers

```javascript
// state-manager.js
export class StateManager {
  constructor(initialState = {}) {
    this.state = initialState;
  }
  
  setState(newState) {
    this.state = { ...this.state, ...newState };
    
    // Notify subscribers
    window.dispatchEvent(new CustomEvent('state-changed', {
      detail: { state: this.state }
    }));
  }
  
  getState() {
    return { ...this.state };
  }
}

// Create a singleton instance
export const appState = new StateManager({
  user: null,
  isAuthenticated: false,
  cart: { items: [], total: 0 }
});

// In a component
import { appState } from '../state-manager.js';

class MyComponent extends LitElement {
  constructor() {
    super();
    this.state = appState.getState();
    
    // Bind the event handler to this instance
    this.handleStateChange = this.handleStateChange.bind(this);
  }
  
  connectedCallback() {
    super.connectedCallback();
    window.addEventListener('state-changed', this.handleStateChange);
  }
  
  disconnectedCallback() {
    super.disconnectedCallback();
    window.removeEventListener('state-changed', this.handleStateChange);
  }
  
  handleStateChange(e) {
    this.state = e.detail.state;
    this.requestUpdate(); // Tell Lit to re-render
  }
  
  // Update the state
  login() {
    appState.setState({
      user: { name: 'John' },
      isAuthenticated: true
    });
  }
}
```

### Simple Routing without Libraries

Create a basic router for vanilla JS apps:

```javascript
// router.js
export class Router {
  constructor(routes) {
    this.routes = routes;
    
    // Handle popstate events (browser back/forward buttons)
    window.addEventListener('popstate', () => this.handleRouteChange());
    
    // Initial route handling
    this.handleRouteChange();
  }
  
  handleRouteChange() {
    const path = window.location.pathname;
    const route = this.findMatchingRoute(path);
    
    if (route) {
      // Dispatch event with route info
      window.dispatchEvent(new CustomEvent('route-changed', {
        detail: { route, params: route.params || {} }
      }));
    }
  }
  
  findMatchingRoute(path) {
    // First try exact matches
    let route = this.routes.find(r => r.path === path);
    if (route) return { ...route, params: {} };
    
    // Then try parameterized routes
    for (const routeConfig of this.routes) {
      if (routeConfig.path.includes(':')) {
        const pathParts = routeConfig.path.split('/');
        const currentParts = path.split('/');
        
        if (pathParts.length !== currentParts.length) continue;
        
        const params = {};
        let match = true;
        
        for (let i = 0; i < pathParts.length; i++) {
          if (pathParts[i].startsWith(':')) {
            // This is a parameter
            const paramName = pathParts[i].substring(1);
            params[paramName] = currentParts[i];
          } else if (pathParts[i] !== currentParts[i]) {
            match = false;
            break;
          }
        }
        
        if (match) {
          return { ...routeConfig, params };
        }
      }
    }
    
    // Return 404 route if defined
    return this.routes.find(r => r.path === '*') || null;
  }
  
  navigateTo(path) {
    window.history.pushState(null, '', path);
    this.handleRouteChange();
  }
}

// Initialize router
const router = new Router([
  { path: '/', component: 'home-view' },
  { path: '/products', component: 'product-list' },
  { path: '/products/:id', component: 'product-detail' },
  { path: '*', component: 'not-found-view' }
]);

// Using the router in a component
class AppShell extends LitElement {
  constructor() {
    super();
    this.currentRoute = { component: 'home-view', params: {} };
    
    // Bind event handlers
    this.handleRouteChange = this.handleRouteChange.bind(this);
  }
  
  connectedCallback() {
    super.connectedCallback();
    window.addEventListener('route-changed', this.handleRouteChange);
  }
  
  disconnectedCallback() {
    super.disconnectedCallback();
    window.removeEventListener('route-changed', this.handleRouteChange);
  }
  
  handleRouteChange(e) {
    this.currentRoute = e.detail.route;
    this.requestUpdate();
  }
  
  render() {
    // Render different components based on route
    switch(this.currentRoute.component) {
      case 'product-list':
        return html`<product-list></product-list>`;
      case 'product-detail':
        return html`<product-detail .productId=${this.currentRoute.params.id}></product-detail>`;
      case 'not-found-view':
        return html`<h1>Page Not Found</h1>`;
      default:
        return html`<home-view></home-view>`;
    }
  }
  
  // Navigation handlers
  navigateToProducts() {
    router.navigateTo('/products');
  }
}
```

## Connecting to a Microservice Architecture

### Working with an API Gateway

Create a simple utility for making API requests:

```javascript
// api-gateway.js
export class ApiGateway {
  constructor(baseUrl = '') {
    this.baseUrl = baseUrl || '/api';
  }
  
  getToken() {
    return localStorage.getItem('authToken') || '';
  }
  
  async request(endpoint, options = {}) {
    const url = `${this.baseUrl}${endpoint}`;
    
    const headers = {
      'Content-Type': 'application/json',
      ...options.headers
    };
    
    // Add auth token if available
    const token = this.getToken();
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    
    const config = {
      ...options,
      headers
    };
    
    try {
      const response = await fetch(url, config);
      
      // Handle non-2xx responses
      if (!response.ok) {
        const error = await response.json().catch(() => ({
          message: response.statusText
        }));
        
        throw new Error(error.message || 'API request failed');
      }
      
      // Handle no content responses
      if (response.status === 204) {
        return null;
      }
      
      return await response.json();
    } catch (error) {
      console.error(`API request error: ${url}`, error);
      throw error;
    }
  }
  
  // Convenience methods
  async get(endpoint, options = {}) {
    return this.request(endpoint, { ...options, method: 'GET' });
  }
  
  async post(endpoint, data, options = {}) {
    return this.request(endpoint, {
      ...options,
      method: 'POST',
      body: JSON.stringify(data)
    });
  }
  
  async put(endpoint, data, options = {}) {
    return this.request(endpoint, {
      ...options,
      method: 'PUT',
      body: JSON.stringify(data)
    });
  }
  
  async patch(endpoint, data, options = {}) {
    return this.request(endpoint, {
      ...options,
      method: 'PATCH',
      body: JSON.stringify(data)
    });
  }
  
  async delete(endpoint, options = {}) {
    return this.request(endpoint, {
      ...options,
      method: 'DELETE'
    });
  }
}

// Example usage
const api = new ApiGateway();

// Products API
export const productsApi = {
  getProducts: (params = {}) => {
    const queryString = new URLSearchParams(params).toString();
    return api.get(`/products${queryString ? `?${queryString}` : ''}`);
  },
  
  getProduct: (id) => api.get(`/products/${id}`),
  
  createProduct: (data) => api.post('/products', data),
  
  updateProduct: (id, data) => api.put(`/products/${id}`, data),
  
  deleteProduct: (id) => api.delete(`/products/${id}`)
};

// Auth API
export const authApi = {
  login: (credentials) => api.post('/auth/login', credentials),
  
  register: (userData) => api.post('/auth/register', userData),
  
  getCurrentUser: () => api.get('/auth/me'),
  
  updateProfile: (data) => api.put('/auth/me', data)
};

// Cart API
export const cartApi = {
  getCart: () => api.get('/cart'),
  
  addItem: (productId, quantity = 1) => api.post('/cart/items', { productId, quantity }),
  
  updateItem: (itemId, quantity) => api.patch(`/cart/items/${itemId}`, { quantity }),
  
  removeItem: (itemId) => api.delete(`/cart/items/${itemId}`),
  
  clearCart: () => api.delete('/cart')
};
```

### Error Handling with Vanilla JS

Create a reusable error handling component:

```javascript
// components/error-boundary.js
import { LitElement, html, css } from 'https://cdn.jsdelivr.net/npm/lit@2.8.0/+esm';

class ErrorBoundary extends LitElement {
  static get properties() {
    return {
      hasError: { type: Boolean },
      errorMessage: { type: String }
    };
  }
  
  static get styles() {
    return css`
      :host {
        display: block;
      }
    `;
  }
  
  constructor() {
    super();
    this.hasError = false;
    this.errorMessage = '';
    
    // Bind error handler
    this.handleError = this.handleError.bind(this);
  }
  
  connectedCallback() {
    super.connectedCallback();
    window.addEventListener('error', this.handleError);
  }
  
  disconnectedCallback() {
    super.disconnectedCallback();
    window.removeEventListener('error', this.handleError);
  }
  
  handleError(event) {
    this.hasError = true;
    this.errorMessage = event.error?.message || 'An error occurred';
    
    // Prevent default browser error handling
    event.preventDefault();
    
    console.error('Caught by error boundary:', event.error);
  }
  
  render() {
    if (this.hasError) {
      return html`
        <wa-callout variant="danger">
          <wa-heading level="4">Something went wrong</wa-heading>
          <p>${this.errorMessage}</p>
          <wa-button @click=${this.reset}>Try Again</wa-button>
        </wa-callout>
      `;
    }
    
    return html`<slot></slot>`;
  }
  
  reset() {
    this.hasError = false;
    this.errorMessage = '';
  }
}

customElements.define('error-boundary', ErrorBoundary);
```

## Testing and Deployment

### ## Testing and Deployment

### Manual Testing

Without a build step, testing is straightforward:

1. Create a simple test page:

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-