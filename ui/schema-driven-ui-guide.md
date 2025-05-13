# Building a Schema-Driven UI System for REST APIs Without Node.js

## Table of Contents

1. [Introduction](#introduction)
2. [Architecture Overview](#architecture-overview)
3. [Schema Discovery API](#schema-discovery-api)
4. [Frontend Implementation](#frontend-implementation)
   - [Schema Service](#schema-service)
   - [Generic Components](#generic-components)
   - [Application Shell](#application-shell)
5. [WebAwesome 3.0 Integration](#webawesome-30-integration)
   - [MutationObserver Pattern](#mutationobserver-pattern)
   - [Reactive UI Updates](#reactive-ui-updates)
   - [Real-time Synchronization](#real-time-synchronization)
6. [Custom Extensions](#custom-extensions)
7. [Advanced Features](#advanced-features)
   - [Relationship Handling](#relationship-handling)
   - [Filtering and Searching](#filtering-and-searching)
   - [Bulk Operations](#bulk-operations)
8. [Best Practices](#best-practices)
9. [Example Implementation](#example-implementation)
10. [Resources](#resources)

## Introduction

A schema-driven UI (also called a metadata-driven UI) is a powerful approach for creating flexible, self-adapting user interfaces that automatically connect to your REST backend services. This approach is particularly valuable for:

- Admin interfaces and dashboards
- Internal tools that need to adapt to changing data models
- Rapid application development where UI requirements evolve quickly
- Large systems with many different entity types

This document explains how to implement such a system using **pure browser technologies** without Node.js, npm, or any build tools. We'll use:

- Native ES modules
- WebAwesome 3.0 UI components
- Vanilla JavaScript
- Lit library (loaded via CDN)
- Web Components standards
- Browser's MutationObserver API

## Architecture Overview

The schema-driven UI system consists of these key parts:

1. **REST Backend with Schema Discovery API**: Your backend exposes endpoints that provide metadata about resources, their properties, and operations.

2. **Schema Service**: A frontend service that fetches, caches, and processes schema metadata.

3. **Generic Components**: A set of flexible web components that adapt based on schema information:
   - Resource List: Shows available resources
   - Generic Table: Displays and manages resource collections
   - Generic Form: Creates and edits resource instances

4. **Custom Extensions**: A mechanism to override or enhance the generic behavior for specific resources.

## Schema Discovery API

The backend needs to expose schema information through a set of endpoints:

```
GET /api/schema                  → List all resource types
GET /api/schema/{resource}       → Get schema for a specific resource
GET /api/schema/{resource}/form  → Get form configuration for resource
GET /api/schema/{resource}/table → Get table configuration for resource
```

### Resource Schema Format

Here's an example schema returned by `/api/schema/users`:

```json
{
  "name": "users",
  "displayName": "Users",
  "description": "System users",
  "properties": {
    "id": {
      "type": "string",
      "format": "uuid",
      "readOnly": true
    },
    "username": {
      "type": "string",
      "maxLength": 50,
      "required": true
    },
    "email": {
      "type": "string",
      "format": "email",
      "required": true
    },
    "role": {
      "type": "string",
      "enum": ["admin", "editor", "viewer"],
      "default": "viewer"
    },
    "active": {
      "type": "boolean",
      "default": true
    },
    "created": {
      "type": "string",
      "format": "date-time",
      "readOnly": true
    }
  },
  "primaryKey": "id",
  "displayField": "username",
  "endpoints": {
    "list": "/api/users",
    "detail": "/api/users/{id}",
    "create": "/api/users",
    "update": "/api/users/{id}",
    "delete": "/api/users/{id}"
  },
  "relationships": {
    "department": {
      "type": "belongsTo",
      "resource": "departments",
      "foreignKey": "departmentId"
    },
    "posts": {
      "type": "hasMany",
      "resource": "posts",
      "foreignKey": "userId"
    }
  },
  "actions": {
    "resetPassword": {
      "endpoint": "/api/users/{id}/reset-password",
      "method": "POST",
      "requiresConfirmation": true,
      "confirmationMessage": "Are you sure you want to reset this user's password?"
    },
    "activate": {
      "endpoint": "/api/users/{id}/activate",
      "method": "POST"
    },
    "deactivate": {
      "endpoint": "/api/users/{id}/deactivate",
      "method": "POST"
    }
  }
}
```

## Frontend Implementation

### Setting Up Without Node.js

Since we're not using Node.js or npm, we'll rely on:

1. **CDN-delivered dependencies**
2. **Browser's native ES modules**
3. **Simple folder structure**
4. **Local web server for development**

#### Local Development Server Options:

1. **Python's built-in HTTP server** (no additional installation needed if Python is installed):
   ```
   # Python 3
   python -m http.server 8000
   
   # Python 2
   python -m SimpleHTTPServer 8000
   ```

2. **Browser extensions**:
   - [Web Server for Chrome](https://chrome.google.com/webstore/detail/web-server-for-chrome/ofhbbkphhbklhfoeikjpcbhemlocgigb)
   - [Live Server for VS Code](https://marketplace.visualstudio.com/items?itemName=ritwickdey.LiveServer)

3. **Deno** (if available):
   ```
   deno run --allow-net --allow-read https://deno.land/std/http/file_server.ts
   ```

4. **Simple browser file access** (with some limitations):
   - Open HTML files directly using the `file://` protocol (Note: some browser security restrictions apply)

### Schema Service

The Schema Service fetches and caches schema information from the backend:

```javascript
// services/schema-service.js
export class SchemaService {
  constructor() {
    this.schemaCache = new Map();
    this.resourceList = null;
  }
  
  async getResources() {
    if (!this.resourceList) {
      const response = await fetch('/api/schema');
      this.resourceList = await response.json();
    }
    return this.resourceList;
  }
  
  async getSchema(resourceName) {
    if (!this.schemaCache.has(resourceName)) {
      const response = await fetch(`/api/schema/${resourceName}`);
      const schema = await response.json();
      this.schemaCache.set(resourceName, schema);
    }
    return this.schemaCache.get(resourceName);
  }
  
  async getFormConfig(resourceName) {
    const response = await fetch(`/api/schema/${resourceName}/form`);
    return response.json();
  }
  
  async getTableConfig(resourceName) {
    const response = await fetch(`/api/schema/${resourceName}/table`);
    return response.json();
  }
}

export const schemaService = new SchemaService();
```

### Generic Components

#### 1. Resource List Component

The Resource List component displays available resources:

```javascript
// components/resource-list.js
import { LitElement, html, css } from 'https://cdn.jsdelivr.net/npm/lit@2.8.0/+esm';
import { schemaService } from '../services/schema-service.js';

class ResourceList extends LitElement {
  static get properties() {
    return {
      resources: { type: Array },
      loading: { type: Boolean }
    };
  }
  
  constructor() {
    super();
    this.resources = [];
    this.loading = true;
  }
  
  async connectedCallback() {
    super.connectedCallback();
    this.loading = true;
    try {
      this.resources = await schemaService.getResources();
    } catch (error) {
      console.error('Failed to load resources:', error);
    } finally {
      this.loading = false;
    }
  }
  
  render() {
    if (this.loading) {
      return html`<wa-spinner></wa-spinner>`;
    }
    
    return html`
      <wa-heading level="1">Resources</wa-heading>
      <div class="resource-grid">
        ${this.resources.map(resource => html`
          <wa-card>
            <wa-heading level="3">${resource.displayName}</wa-heading>
            <p>${resource.description}</p>
            <wa-button @click=${() => this.navigateToResource(resource.name)}>
              Manage ${resource.displayName}
            </wa-button>
          </wa-card>
        `)}
      </div>
    `;
  }
  
  navigateToResource(resourceName) {
    const event = new CustomEvent('navigate', {
      detail: { path: `/resources/${resourceName}` },
      bubbles: true,
      composed: true
    });
    this.dispatchEvent(event);
  }
}

customElements.define('resource-list', ResourceList);
```

#### 2. Generic Table Component

The Generic Table component displays a list of resource items with CRUD operations.

#### 3. Generic Form Component

The Generic Form component creates and edits resource instances.

### Application Shell

The Application Shell ties everything together and handles routing.

## WebAwesome 3.0 Integration

WebAwesome 3.0 provides powerful capabilities that make it particularly well-suited for schema-driven UIs. One of its most valuable features is the integration of the MutationObserver API, which enables the creation of reactive UIs that automatically respond to changes in the DOM.

### MutationObserver Pattern

The MutationObserver API is a browser feature that allows you to watch for changes in the DOM tree. WebAwesome 3.0 leverages this pattern to create a reactive UI system that can respond to both user interactions and server-side data changes.

#### Observer Component

Create a dedicated observer component that monitors DOM changes and reacts accordingly:

```javascript
// components/schema-observer.js
import { LitElement, html } from 'https://cdn.jsdelivr.net/npm/lit@2.8.0/+esm';
import { allDefined } from 'https://early.webawesome.com/webawesome@3.0.0-alpha.12/dist/webawesome.js';

class SchemaObserver extends LitElement {
  static get properties() {
    return {
      resourceName: { type: String },
      lastUpdate: { type: Number }
    };
  }
  
  constructor() {
    super();
    this.resourceName = '';
    this.lastUpdate = Date.now();
    this.observer = null;
  }
  
  connectedCallback() {
    super.connectedCallback();
    
    // Wait for WebAwesome components to be fully defined
    allDefined().then(() => {
      this.setupObserver();
    });
  }
  
  disconnectedCallback() {
    super.disconnectedCallback();
    
    // Clean up the observer to prevent memory leaks
    if (this.observer) {
      this.observer.disconnect();
      this.observer = null;
    }
  }
  
  setupObserver() {
    // Target the resource container to observe
    const targetSelector = `[data-resource="${this.resourceName}"]`;
    const targetElement = document.querySelector(targetSelector);
    
    if (!targetElement) {
      console.warn(`No element found for resource: ${this.resourceName}`);
      return;
    }
    
    // Create a configuration object
    const config = {
      attributes: true,      // Watch for attribute changes
      childList: true,       // Watch for child additions/removals
      subtree: true,         // Apply to all descendants
      attributeFilter: ['data-state', 'data-modified'] // Only specific attributes
    };
    
    // Create the observer with a callback
    this.observer = new MutationObserver((mutations) => {
      for (const mutation of mutations) {
        this.handleMutation(mutation);
      }
    });
    
    // Start observing
    this.observer.observe(targetElement, config);
    console.log(`Observer started for ${this.resourceName}`);
  }
  
  handleMutation(mutation) {
    // Update timestamp to trigger component re-render
    this.lastUpdate = Date.now();
    
    if (mutation.type === 'attributes') {
      const target = mutation.target;
      const attributeName = mutation.attributeName;
      const newValue = target.getAttribute(attributeName);
      const oldValue = mutation.oldValue;
      
      console.log(`Attribute changed: ${attributeName}`, {
        old: oldValue,
        new: newValue,
        element: target
      });
      
      // Handle specific attribute changes
      if (attributeName === 'data-state') {
        this.handleStateChange(target, oldValue, newValue);
      } else if (attributeName === 'data-modified') {
        this.handleModificationChange(target, oldValue, newValue);
      }
    } else if (mutation.type === 'childList') {
      if (mutation.addedNodes.length > 0) {
        console.log('Elements added:', mutation.addedNodes);
        this.handleAddedNodes(mutation.addedNodes);
      }
      
      if (mutation.removedNodes.length > 0) {
        console.log('Elements removed:', mutation.removedNodes);
        this.handleRemovedNodes(mutation.removedNodes);
      }
    }
    
    // Dispatch a custom event for other components to react to
    this.dispatchEvent(new CustomEvent('resource-changed', {
      bubbles: true,
      composed: true,
      detail: {
        resourceName: this.resourceName,
        mutation,
        timestamp: this.lastUpdate
      }
    }));
  }
  
  // Various handler methods for mutations
  // ...
  
  render() {
    // This component doesn't render any visible UI
    return html``;
  }
}

customElements.define('schema-observer', SchemaObserver);
```

### Reactive UI Updates

Use the MutationObserver pattern to create reactive UI components that automatically update when schema data changes.

### Real-time Synchronization

Combine MutationObserver with WebSockets to create a real-time synchronized UI.

## Custom Extensions

While generic components provide a solid foundation, you'll often need custom behavior for specific resources. The extension system enables this without modifying the core components.

### Extension Service

```javascript
// custom-extensions.js
import { html } from 'https://cdn.jsdelivr.net/npm/lit@2.8.0/+esm';

export const extensions = {
  // Custom extensions for the 'users' resource
  users: {
    // Custom action handlers
    actions: {
      resetPassword: async (userId) => {
        // Custom implementation for reset password
        console.log('Custom reset password for user', userId);
        
        // Call the API
        const response = await fetch(`/api/users/${userId}/reset-password`, {
          method: 'POST'
        });
        
        return response.json();
      }
    },
    
    // Custom form field renderers
    renderFields: {
      password: (fieldName, property, value, onChange, error) => {
        return html`
          <div class="password-field">
            <wa-input
              type="password"
              label="${property.displayName || fieldName}"
              ?required=${property.required}
              .value=${value}
              @wa-input=${onChange}
              ?invalid=${!!error}
              error-text=${error || ''}
            ></wa-input>
            <wa-button size="small" type="button">Generate</wa-button>
          </div>
        `;
      }
    },
    
    // Custom validation logic
    validate: (formData, schema) => {
      const errors = {};
      
      // Custom validation for password fields
      if (formData.password && formData.password.length < 8) {
        errors.password = 'Password must be at least 8 characters long';
      }
      
      if (formData.password && formData.passwordConfirm && 
          formData.password !== formData.passwordConfirm) {
        errors.passwordConfirm = 'Passwords do not match';
      }
      
      return errors;
    }
  },
  
  // More resource-specific extensions
  // ...
};
```

## Advanced Features

### Relationship Handling

One of the most important features of a generic UI system is handling relationships between resources.

### Filtering and Searching

Adding search and filter capabilities is essential for tables with many rows.

### Bulk Operations

For efficiency, enable bulk operations on multiple selected items.

## Best Practices

### 1. Schema Design

- **Be consistent with property types**: Use the same data types for similar fields across resources
- **Include meaningful display names**: Don't rely on field names for UI display
- **Use enums for fixed value sets**: Define allowed values for fields with a fixed set of options
- **Document relationships clearly**: Include all necessary information for relationship handling
- **Provide sensible defaults**: Set default values where appropriate to improve UX

### 2. Performance Optimization

- **Cache schemas**: Store schemas in memory to avoid repeated requests
- **Use pagination**: Always paginate large collections
- **Implement virtual scrolling**: For very large tables, consider virtual scrolling
- **Lazy load related resources**: Only fetch related data when needed
- **Use JSON schema $ref for shared definitions**: Avoid duplication in your schemas

### 3. Security Considerations

- **Include permissions in schema**: Define what operations are allowed for each resource
- **Validate inputs on both client and server**: Never trust client-side validation alone
- **Use HTTPS for all API calls**: Secure data in transit
- **Implement proper authentication**: Include authentication tokens in requests
- **Respect CORS headers**: Set up proper cross-origin resource sharing

### 4. Extensibility

- **Design for composition**: Make components composable and reusable
- **Use the extension system**: Avoid modifying core components directly
- **Keep extensions resource-specific**: Organize extensions by resource name
- **Document extension points**: Make it clear how to extend components

### 5. Accessibility

- **Use proper ARIA attributes**: Make generic UI accessible
- **Test with screen readers**: Verify accessibility with real assistive technologies
- **Support keyboard navigation**: Ensure all functionality works with keyboard
- **Follow color contrast guidelines**: Make sure text is readable
- **Provide text alternatives**: Always include alt text for images

### 6. MutationObserver Best Practices

- **Be selective with observers**: Only observe elements that need observation to avoid performance issues
- **Use attribute filters**: Specify which attributes to watch rather than observing all changes
- **Clean up observers**: Always disconnect observers when components are removed
- **Batch DOM updates**: Group related updates to reduce the number of mutations
- **Use debouncing**: Debounce mutation handlers for performance-intensive operations
- **Use data attributes for state**: Store state in data attributes to make it observable
- **Structure event handling**: Create a clean system of custom events for mutations
- **Use requestAnimationFrame**: Defer UI updates to the next paint cycle for smoother animations

## Example Implementation

### 1. Project Structure

```
schema-driven-ui/
├── index.html                # Main HTML file
├── components/               # Web components
│   ├── resource-list.js      # List available resources
│   ├── generic-table.js      # Display and manage resource collections
│   ├── generic-form.js       # Create and edit resource instances
│   ├── schema-observer.js    # MutationObserver component
│   ├── sync-observer.js      # WebSocket synchronization
│   ├── reactive-resource-view.js # Reactive resource view
│   └── app-shell.js          # Main application component
├── services/                 # Service layer
│   ├── schema-service.js     # Fetch and process schemas
│   ├── sync-service.js       # Real-time synchronization
│   └── custom-extensions.js  # Custom behaviors for specific resources
└── styles/                   # Optional global styles
    └── main.css              # Global CSS
```

### 2. HTML Entry Point

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Schema-Driven Admin Dashboard</title>
  
  <!-- WebAwesome 3.0 -->
  <link rel="stylesheet" href="https://early.webawesome.com/webawesome@3.0.0-alpha.12/dist/styles/themes/default.css" />
  <link rel="stylesheet" href="https://early.webawesome.com/webawesome@3.0.0-alpha.12/dist/styles/webawesome.css" />
  <script type="module" src="https://early.webawesome.com/webawesome@3.0.0-alpha.12/dist/webawesome.loader.js"></script>
  
  <!-- Lit Library from CDN -->
  <script type="module" src="https://cdn.jsdelivr.net/npm/lit@2.8.0/+esm"></script>
  
  <!-- Application component (which imports everything else) -->
  <script type="module" src="./components/app-shell.js"></script>
  
  <!-- Global styles -->
  <link rel="stylesheet" href="./styles/main.css">
</head>
<body>
  <app-shell></app-shell>
</body>
</html>
```

### 3. Running Locally (Without Node.js)

#### Using Python's built-in HTTP server:

1. Open your terminal/command prompt
2. Navigate to the `schema-driven-ui` directory
3. Run the appropriate command:

```bash
# Python 3
python -m http.server 8000

# Python 2
python -m SimpleHTTPServer 8000
```

4. Open a browser and navigate to `http://localhost:8000`

#### Using browser file protocol (with limitations):

1. Simply open the `index.html` file directly in your browser using `file://` protocol
2. Note: Some browser features like fetch API might be restricted due to CORS policy when using file protocol

### 4. Deployment

Since we're using a pure browser-based approach without build steps, deployment is straightforward:

1. Upload all files as-is to any static web hosting service:
   - GitHub Pages
   - Netlify
   - Vercel
   - Amazon S3
   - Any standard web hosting

2. If using client-side routing, configure your hosting service for proper routing:

For Netlify, create a `_redirects` file:
```
/*    /index.html   200
```

For GitHub Pages, create a `404.html` that redirects to `index.html`

### 5. Browser Support Considerations

Since we're using modern browser features without transpilation:

- ES Modules: Supported in all modern browsers
- Web Components: Supported in all modern browsers
- Fetch API: Supported in all modern browsers
- MutationObserver: Supported in all modern browsers

For older browsers, consider adding the following polyfills from CDN:
```html
<!-- For older browsers -->
<script src="https://unpkg.com/@webcomponents/webcomponentsjs@2.5.0/webcomponents-bundle.js"></script>
<script src="https://unpkg.com/whatwg-fetch@3.6.2/dist/fetch.umd.js"></script>
```

## Resources

- [JSON Schema](https://json-schema.org/) - Format for describing JSON data
- [OpenAPI Specification](https://swagger.io/specification/) - Another approach to API description
- [Web Components MDN Guide](https://developer.mozilla.org/en-US/docs/Web/API/Web_components)
- [Lit Documentation](https://lit.dev/)
- [WebAwesome Documentation](https://backers.webawesome.com/docs/)
- [MutationObserver API](https://developer.mozilla.org/en-US/docs/Web/API/MutationObserver) - Core browser API for observing DOM changes
- [WebAwesome 3.0 GitHub](https://github.com/shoelace-style/webawesome-alpha) - Repository for WebAwesome 3.0
- [ES Modules in Browsers](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide/Modules) - Using ES modules directly in browsers

## Conclusion

By implementing this schema-driven UI system with WebAwesome 3.0 and MutationObserver integration using only browser technologies (no Node.js required), you create a powerful, self-adapting interface that automatically responds to changes in your REST API and provides real-time updates.

Key benefits of this approach include:

1. **No Build Tools Required**: Pure browser-based development with ES modules
2. **Automatic UI Generation**: Components adapt based on schema metadata
3. **Real-time Reactivity**: The MutationObserver pattern enables automatic UI updates
4. **Bidirectional Synchronization**: Changes propagate from UI to server and from server to UI in real-time
5. **Simplified Development**: Edit-and-refresh workflow without compilation
6. **Standards-Based**: Built on web standards for future compatibility
7. **Easy Deployment**: Upload files as-is to any static hosting

This approach is particularly valuable for teams who want to avoid complex build tooling while still creating modern, reactive web applications that can adapt to evolving REST APIs.# Building a Schema-Driven UI System for REST APIs

## Table of Contents

1. [Introduction](#introduction)
2. [Architecture Overview](#architecture-overview)
3. [Schema Discovery API](#schema-discovery-api)
4. [Frontend Implementation](#frontend-implementation)
   - [Schema Service](#schema-service)
   - [Generic Components](#generic-components)
   - [Application Shell](#application-shell)
5. [WebAwesome 3.0 Integration](#webawesome-30-integration)
   - [MutationObserver Pattern](#mutationobserver-pattern)
   - [Reactive UI Updates](#reactive-ui-updates)
   - [Real-time Synchronization](#real-time-synchronization)
6. [Custom Extensions](#custom-extensions)
7. [Advanced Features](#advanced-features)
   - [Relationship Handling](#relationship-handling)
   - [Filtering and Searching](#filtering-and-searching)
   - [Bulk Operations](#bulk-operations)
8. [Best Practices](#best-practices)
9. [Example Implementation](#example-implementation)
10. [Resources](#resources)

## Introduction

A schema-driven UI (also called a metadata-driven UI) is a powerful approach for creating flexible, self-adapting user interfaces that automatically connect to your REST backend services. This approach is particularly valuable for:

- Admin interfaces and dashboards
- Internal tools that need to adapt to changing data models
- Rapid application development where UI requirements evolve quickly
- Large systems with many different entity types

Instead of manually creating UI components for each entity in your system, a schema-driven approach uses metadata from the backend to dynamically generate appropriate UI elements. This documentation explains how to implement such a system using web components, WebAwesome UI library, and vanilla JavaScript.

## Architecture Overview

The schema-driven UI system consists of these key parts:

1. **REST Backend with Schema Discovery API**: Your backend exposes endpoints that provide metadata about resources, their properties, and operations.

2. **Schema Service**: A frontend service that fetches, caches, and processes schema metadata.

3. **Generic Components**: A set of flexible web components that adapt based on schema information:
   - Resource List: Shows available resources
   - Generic Table: Displays and manages resource collections
   - Generic Form: Creates and edits resource instances

4. **Custom Extensions**: A mechanism to override or enhance the generic behavior for specific resources.

![Architecture Diagram](https://i.imgur.com/placeholder.png)

## Schema Discovery API

The backend needs to expose schema information through a set of endpoints:

```
GET /api/schema                  → List all resource types
GET /api/schema/{resource}       → Get schema for a specific resource
GET /api/schema/{resource}/form  → Get form configuration for resource
GET /api/schema/{resource}/table → Get table configuration for resource
```

### Resource Schema Format

Here's an example schema returned by `/api/schema/users`:

```json
{
  "name": "users",
  "displayName": "Users",
  "description": "System users",
  "properties": {
    "id": {
      "type": "string",
      "format": "uuid",
      "readOnly": true
    },
    "username": {
      "type": "string",
      "maxLength": 50,
      "required": true
    },
    "email": {
      "type": "string",
      "format": "email",
      "required": true
    },
    "role": {
      "type": "string",
      "enum": ["admin", "editor", "viewer"],
      "default": "viewer"
    },
    "active": {
      "type": "boolean",
      "default": true
    },
    "created": {
      "type": "string",
      "format": "date-time",
      "readOnly": true
    }
  },
  "primaryKey": "id",
  "displayField": "username",
  "endpoints": {
    "list": "/api/users",
    "detail": "/api/users/{id}",
    "create": "/api/users",
    "update": "/api/users/{id}",
    "delete": "/api/users/{id}"
  },
  "relationships": {
    "department": {
      "type": "belongsTo",
      "resource": "departments",
      "foreignKey": "departmentId"
    },
    "posts": {
      "type": "hasMany",
      "resource": "posts",
      "foreignKey": "userId"
    }
  },
  "actions": {
    "resetPassword": {
      "endpoint": "/api/users/{id}/reset-password",
      "method": "POST",
      "requiresConfirmation": true,
      "confirmationMessage": "Are you sure you want to reset this user's password?"
    },
    "activate": {
      "endpoint": "/api/users/{id}/activate",
      "method": "POST"
    },
    "deactivate": {
      "endpoint": "/api/users/{id}/deactivate",
      "method": "POST"
    }
  },
  "filters": [
    {
      "field": "role",
      "label": "Role",
      "type": "select",
      "options": [
        {"value": "admin", "label": "Admin"},
        {"value": "editor", "label": "Editor"},
        {"value": "viewer", "label": "Viewer"}
      ]
    },
    {
      "field": "active",
      "label": "Status",
      "type": "boolean"
    }
  ],
  "bulkActions": {
    "activate": {
      "endpoint": "/api/users/bulk-activate",
      "method": "POST",
      "label": "Activate Users"
    },
    "deactivate": {
      "endpoint": "/api/users/bulk-deactivate",
      "method": "POST",
      "label": "Deactivate Users"
    }
  }
}
```

The schema contains:

- Basic metadata (name, displayName, description)
- Property definitions with types, validation rules, etc.
- Primary key and display field information
- Endpoint URLs for CRUD operations
- Relationship definitions
- Custom actions
- Filter configurations
- Bulk operation definitions

## Frontend Implementation

### Schema Service

The Schema Service fetches and caches schema information from the backend:

```javascript
// schema-service.js
export class SchemaService {
  constructor() {
    this.schemaCache = new Map();
    this.resourceList = null;
  }
  
  async getResources() {
    if (!this.resourceList) {
      const response = await fetch('/api/schema');
      this.resourceList = await response.json();
    }
    return this.resourceList;
  }
  
  async getSchema(resourceName) {
    if (!this.schemaCache.has(resourceName)) {
      const response = await fetch(`/api/schema/${resourceName}`);
      const schema = await response.json();
      this.schemaCache.set(resourceName, schema);
    }
    return this.schemaCache.get(resourceName);
  }
  
  async getFormConfig(resourceName) {
    const response = await fetch(`/api/schema/${resourceName}/form`);
    return response.json();
  }
  
  async getTableConfig(resourceName) {
    const response = await fetch(`/api/schema/${resourceName}/table`);
    return response.json();
  }
}

export const schemaService = new SchemaService();
```

### Generic Components

#### 1. Resource List Component

The Resource List component displays available resources:

```javascript
// resource-list.js
import { LitElement, html, css } from 'https://cdn.jsdelivr.net/npm/lit@2.8.0/+esm';
import { schemaService } from '../services/schema-service.js';

class ResourceList extends LitElement {
  static get properties() {
    return {
      resources: { type: Array },
      loading: { type: Boolean }
    };
  }
  
  constructor() {
    super();
    this.resources = [];
    this.loading = true;
  }
  
  async connectedCallback() {
    super.connectedCallback();
    this.loading = true;
    try {
      this.resources = await schemaService.getResources();
    } catch (error) {
      console.error('Failed to load resources:', error);
    } finally {
      this.loading = false;
    }
  }
  
  render() {
    if (this.loading) {
      return html`<wa-spinner></wa-spinner>`;
    }
    
    return html`
      <wa-heading level="1">Resources</wa-heading>
      <div class="resource-grid">
        ${this.resources.map(resource => html`
          <wa-card>
            <wa-heading level="3">${resource.displayName}</wa-heading>
            <p>${resource.description}</p>
            <wa-button @click=${() => this.navigateToResource(resource.name)}>
              Manage ${resource.displayName}
            </wa-button>
          </wa-card>
        `)}
      </div>
    `;
  }
  
  navigateToResource(resourceName) {
    const event = new CustomEvent('navigate', {
      detail: { path: `/resources/${resourceName}` },
      bubbles: true,
      composed: true
    });
    this.dispatchEvent(event);
  }
}

customElements.define('resource-list', ResourceList);
```

#### 2. Generic Table Component

The Generic Table component displays a list of resource items and supports various operations:

```javascript
// generic-table.js
import { LitElement, html, css } from 'https://cdn.jsdelivr.net/npm/lit@2.8.0/+esm';
import { schemaService } from '../services/schema-service.js';
import { extensions } from '../services/custom-extensions.js';

class GenericTable extends LitElement {
  static get properties() {
    return {
      resourceName: { type: String },
      items: { type: Array },
      schema: { type: Object },
      tableConfig: { type: Object },
      loading: { type: Boolean },
      sortField: { type: String },
      sortDirection: { type: String },
      page: { type: Number },
      pageSize: { type: Number },
      totalItems: { type: Number },
      selectedItems: { type: Object },
      filters: { type: Object },
      searchTerm: { type: String }
    };
  }
  
  constructor() {
    super();
    this.items = [];
    this.schema = null;
    this.tableConfig = null;
    this.loading = true;
    this.sortField = '';
    this.sortDirection = 'asc';
    this.page = 1;
    this.pageSize = 10;
    this.totalItems = 0;
    this.selectedItems = new Set();
    this.filters = {};
    this.searchTerm = '';
  }
  
  async connectedCallback() {
    super.connectedCallback();
    await this.loadSchema();
    this.setupFilters();
    await this.loadItems();
  }
  
  async loadSchema() {
    try {
      [this.schema, this.tableConfig] = await Promise.all([
        schemaService.getSchema(this.resourceName),
        schemaService.getTableConfig(this.resourceName)
      ]);
    } catch (error) {
      console.error(`Failed to load schema for ${this.resourceName}:`, error);
    }
  }
  
  setupFilters() {
    // Set up default filters based on schema
    if (this.schema && this.schema.filters) {
      this.schema.filters.forEach(filter => {
        if (filter.default) {
          this.filters[filter.field] = filter.default;
        }
      });
    }
  }
  
  async loadItems() {
    this.loading = true;
    
    try {
      // Build the query string with pagination, sorting, etc.
      const params = new URLSearchParams({
        _page: this.page.toString(),
        _limit: this.pageSize.toString()
      });
      
      if (this.sortField) {
        const sortPrefix = this.sortDirection === 'desc' ? '-' : '';
        params.append('_sort', `${sortPrefix}${this.sortField}`);
      }
      
      // Add search term if present
      if (this.searchTerm) {
        params.append('q', this.searchTerm);
      }
      
      // Add filters
      Object.entries(this.filters).forEach(([key, value]) => {
        if (value !== null && value !== undefined && value !== '') {
          params.append(key, value);
        }
      });
      
      const endpoint = this.schema.endpoints.list;
      const response = await fetch(`${endpoint}?${params.toString()}`);
      
      // Handle pagination headers
      const totalItems = response.headers.get('X-Total-Count');
      if (totalItems) {
        this.totalItems = parseInt(totalItems, 10);
      }
      
      this.items = await response.json();
    } catch (error) {
      console.error(`Failed to load items for ${this.resourceName}:`, error);
    } finally {
      this.loading = false;
    }
  }
  
  handleSort(field) {
    if (this.sortField === field) {
      // Toggle direction
      this.sortDirection = this.sortDirection === 'asc' ? 'desc' : 'asc';
    } else {
      this.sortField = field;
      this.sortDirection = 'asc';
    }
    
    this.loadItems();
  }
  
  handlePageChange(newPage) {
    this.page = newPage;
    this.loadItems();
  }
  
  handleSearch(e) {
    this.searchTerm = e.target.value;
    this.page = 1; // Reset to first page
    this.loadItems();
  }
  
  handleFilterChange(field, e) {
    this.filters = {
      ...this.filters,
      [field]: e.target.value
    };
    
    this.page = 1; // Reset to first page
    this.loadItems();
  }
  
  toggleSelectAll(e) {
    if (e.target.checked) {
      // Select all items
      this.selectedItems = new Set(this.items.map(item => item[this.schema.primaryKey]));
    } else {
      // Deselect all
      this.selectedItems.clear();
    }
    
    this.requestUpdate();
  }
  
  toggleSelectItem(itemId, e) {
    if (e.target.checked) {
      this.selectedItems.add(itemId);
    } else {
      this.selectedItems.delete(itemId);
    }
    
    this.requestUpdate();
  }
  
  // More methods for CRUD operations, bulk actions, etc.
  
  render() {
    if (!this.schema || this.loading) {
      return html`<wa-spinner></wa-spinner>`;
    }
    
    const visibleColumns = this.tableConfig?.columns || 
      Object.entries(this.schema.properties)
        .filter(([_, prop]) => !prop.hidden)
        .map(([name, prop]) => ({
          field: name,
          header: prop.displayName || name,
          sortable: !prop.readOnly
        }));
    
    return html`
      <div class="table-container">
        <div class="table-header">
          <wa-heading level="2">${this.schema.displayName}</wa-heading>
          <wa-button variant="brand" @click=${this.handleCreate}>
            Create ${this.schema.displayName}
          </wa-button>
        </div>
        
        <div class="table-filters">
          <wa-input
            type="search"
            placeholder="Search..."
            .value=${this.searchTerm}
            @wa-input=${this.handleSearch}
          >
            <wa-icon slot="prefix" name="search"></wa-icon>
          </wa-input>
          
          ${this.schema.filters ? this.schema.filters.map(filter => this.renderFilter(filter)) : ''}
        </div>
        
        <div class="bulk-actions">
          ${this.selectedItems.size > 0 ? html`
            <div class="selection-info">
              ${this.selectedItems.size} item(s) selected
            </div>
            
            <div class="bulk-buttons">
              <wa-button 
                variant="danger" 
                size="small"
                @click=${() => this.handleBulkAction('delete')}
              >
                Delete Selected
              </wa-button>
              
              ${this.schema.bulkActions ? Object.entries(this.schema.bulkActions).map(
                ([name, action]) => html`
                  <wa-button 
                    size="small"
                    @click=${() => this.handleBulkAction(name)}
                  >
                    ${action.label || name}
                  </wa-button>
                `
              ) : ''}
            </div>
          ` : ''}
        </div>
        
        <wa-data-table>
          <wa-table-header>
            <wa-table-header-cell>
              <wa-checkbox 
                @wa-change=${this.toggleSelectAll}
                ?checked=${this.selectedItems.size === this.items.length && this.items.length > 0}
                ?indeterminate=${this.selectedItems.size > 0 && this.selectedItems.size < this.items.length}
              ></wa-checkbox>
            </wa-table-header-cell>
            
            ${visibleColumns.map(column => html`
              <wa-table-header-cell 
                ?sortable=${column.sortable}
                ?sorted=${this.sortField === column.field}
                sort-direction=${this.sortField === column.field ? this.sortDirection : ''}
                @click=${() => this.handleSort(column.field)}
              >
                ${column.header}
              </wa-table-header-cell>
            `)}
            <wa-table-header-cell>Actions</wa-table-header-cell>
          </wa-table-header>
          
          <wa-table-body>
            ${this.items.map(item => html`
              <wa-table-row>
                <wa-table-cell>
                  <wa-checkbox 
                    @wa-change=${e => this.toggleSelectItem(item[this.schema.primaryKey], e)}
                    ?checked=${this.selectedItems.has(item[this.schema.primaryKey])}
                  ></wa-checkbox>
                </wa-table-cell>
                
                ${visibleColumns.map(column => html`
                  <wa-table-cell>
                    ${this.formatCellValue(item[column.field], this.schema.properties[column.field], item, column.field)}
                  </wa-table-cell>
                `)}
                
                <wa-table-cell>
                  <div class="actions">
                    <wa-button size="small" @click=${() => this.handleEdit(item)}>
                      Edit
                    </wa-button>
                    <wa-button 
                      size="small" 
                      variant="danger" 
                      @click=${() => this.handleDelete(item)}
                    >
                      Delete
                    </wa-button>
                    
                    ${this.schema.actions ? Object.entries(this.schema.actions).map(([name, action]) => html`
                      <wa-button 
                        size="small" 
                        @click=${() => this.handleCustomAction(action, item, name)}
                      >
                        ${name}
                      </wa-button>
                    `) : ''}
                  </div>
                </wa-table-cell>
              </wa-table-row>
            `)}
          </wa-table-body>
        </wa-data-table>
        
        <wa-pagination
          current-page=${this.page}
          total-pages=${Math.ceil(this.totalItems / this.pageSize)}
          @change=${e => this.handlePageChange(e.detail.page)}
        ></wa-pagination>
      </div>
    `;
  }
  
  formatCellValue(value, propertySchema, item, field) {
    // Check for custom renderer
    const resourceExtensions = extensions[this.resourceName] || {};
    const customRenderers = resourceExtensions.renderCells || {};
    
    if (customRenderers[field]) {
      return customRenderers[field](value, item, propertySchema);
    }
    
    // Standard formatting based on property type
    if (value === null || value === undefined) {
      return '';
    }
    
    if (propertySchema.format === 'date-time') {
      return new Date(value).toLocaleString();
    }
    
    if (propertySchema.format === 'date') {
      return new Date(value).toLocaleDateString();
    }
    
    if (propertySchema.type === 'boolean') {
      return html`<wa-badge variant=${value ? 'success' : 'danger'}>
        ${value ? 'Yes' : 'No'}
      </wa-badge>`;
    }
    
    return value.toString();
  }
  
  renderFilter(filter) {
    const value = this.filters[filter.field] || '';
    
    if (filter.type === 'select') {
      return html`
        <wa-select
          label="${filter.label}"
          .value=${value}
          @wa-change=${e => this.handleFilterChange(filter.field, e)}
        >
          <wa-option value="">All</wa-option>
          ${filter.options.map(option => html`
            <wa-option value="${option.value}">${option.label}</wa-option>
          `)}
        </wa-select>
      `;
    }
    
    // Other filter types...
    
    return null;
  }
  
  // Navigation handlers
  handleCreate() {
    this.dispatchEvent(new CustomEvent('navigate', {
      detail: { path: `/resources/${this.resourceName}/create` },
      bubbles: true,
      composed: true
    }));
  }
  
  handleEdit(item) {
    this.dispatchEvent(new CustomEvent('navigate', {
      detail: { 
        path: `/resources/${this.resourceName}/edit/${item[this.schema.primaryKey]}`
      },
      bubbles: true,
      composed: true
    }));
  }
}

customElements.define('generic-table', GenericTable);
```

#### 3. Generic Form Component

The Generic Form component creates and edits resource items:

```javascript
// generic-form.js
import { LitElement, html, css } from 'https://cdn.jsdelivr.net/npm/lit@2.8.0/+esm';
import { schemaService } from '../services/schema-service.js';
import { extensions } from '../services/custom-extensions.js';

class GenericForm extends LitElement {
  static get properties() {
    return {
      resourceName: { type: String },
      itemId: { type: String },
      schema: { type: Object },
      formConfig: { type: Object },
      formData: { type: Object },
      loading: { type: Boolean },
      saving: { type: Boolean },
      errors: { type: Object }
    };
  }
  
  constructor() {
    super();
    this.schema = null;
    this.formConfig = null;
    this.formData = {};
    this.loading = true;
    this.saving = false;
    this.errors = {};
  }
  
  async connectedCallback() {
    super.connectedCallback();
    await this.loadSchema();
    
    if (this.itemId) {
      await this.loadItem();
    } else {
      // Set default values for new item
      this.formData = Object.entries(this.schema.properties).reduce((data, [key, prop]) => {
        if (prop.default !== undefined) {
          data[key] = prop.default;
        }
        return data;
      }, {});
      this.loading = false;
    }
  }
  
  async loadSchema() {
    try {
      [this.schema, this.formConfig] = await Promise.all([
        schemaService.getSchema(this.resourceName),
        schemaService.getFormConfig(this.resourceName)
      ]);
    } catch (error) {
      console.error(`Failed to load schema for ${this.resourceName}:`, error);
    }
  }
  
  async loadItem() {
    this.loading = true;
    
    try {
      const endpoint = this.schema.endpoints.detail.replace('{id}', this.itemId);
      const response = await fetch(endpoint);
      this.formData = await response.json();
    } catch (error) {
      console.error(`Failed to load item:`, error);
      
      this.dispatchEvent(new CustomEvent('show-toast', {
        detail: { message: `Failed to load item`, variant: 'danger' },
        bubbles: true,
        composed: true
      }));
    } finally {
      this.loading = false;
    }
  }
  
  async handleSubmit(e) {
    e.preventDefault();
    
    // Validate the form
    if (!this.validateForm()) {
      return;
    }
    
    this.saving = true;
    
    try {
      const isNewItem = !this.itemId;
      const endpoint = isNewItem 
        ? this.schema.endpoints.create
        : this.schema.endpoints.update.replace('{id}', this.itemId);
      
      const response = await fetch(endpoint, {
        method: isNewItem ? 'POST' : 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(this.formData)
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.message || 'An error occurred');
      }
      
      // Show success message
      this.dispatchEvent(new CustomEvent('show-toast', {
        detail: { 
          message: `${this.schema.displayName} ${isNewItem ? 'created' : 'updated'} successfully`, 
          variant: 'success' 
        },
        bubbles: true,
        composed: true
      }));
      
      // Navigate back to list view
      this.dispatchEvent(new CustomEvent('navigate', {
        detail: { path: `/resources/${this.resourceName}` },
        bubbles: true,
        composed: true
      }));
    } catch (error) {
      console.error(`Failed to save ${this.schema.displayName}:`, error);
      
      this.dispatchEvent(new CustomEvent('show-toast', {
        detail: { 
          message: `Failed to save ${this.schema.displayName}: ${error.message}`, 
          variant: 'danger' 
        },
        bubbles: true,
        composed: true
      }));
    } finally {
      this.saving = false;
    }
  }
  
  validateForm() {
    this.errors = {};
    let isValid = true;
    
    // Check each property for validation rules
    Object.entries(this.schema.properties).forEach(([key, prop]) => {
      // Skip read-only fields
      if (prop.readOnly) return;
      
      const value = this.formData[key];
      
      // Required check
      if (prop.required && (value === undefined || value === null || value === '')) {
        this.errors[key] = `${prop.displayName || key} is required`;
        isValid = false;
        return;
      }
      
      // Type-specific validations
      if (value !== undefined && value !== null) {
        if (prop.type === 'string') {
          if (prop.minLength && value.length < prop.minLength) {
            this.errors[key] = `Minimum length is ${prop.minLength}`;
            isValid = false;
          }
          
          if (prop.maxLength && value.length > prop.maxLength) {
            this.errors[key] = `Maximum length is ${prop.maxLength}`;
            isValid = false;
          }
          
          if (prop.format === 'email' && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)) {
            this.errors[key] = 'Invalid email format';
            isValid = false;
          }
        }
        
        // More validations...
      }
    });
    
    // Apply custom validation if available
    const resourceExtensions = extensions[this.resourceName] || {};
    if (resourceExtensions.validate) {
      const customErrors = resourceExtensions.validate(this.formData, this.schema);
      if (Object.keys(customErrors).length > 0) {
        this.errors = { ...this.errors, ...customErrors };
        isValid = false;
      }
    }
    
    this.requestUpdate();
    
    return isValid;
  }
  
  handleInputChange(field, event) {
    const value = this.getInputValue(event.target, this.schema.properties[field]);
    this.formData = {
      ...this.formData,
      [field]: value
    };
    
    // Clear error when field is edited
    if (this.errors[field]) {
      this.errors = {
        ...this.errors,
        [field]: null
      };
    }
  }
  
  getInputValue(input, propertySchema) {
    if (input.type === 'checkbox') {
      return input.checked;
    }
    
    if (propertySchema.type === 'number') {
      return input.value === '' ? null : Number(input.value);
    }
    
    return input.value;
  }
  
  render() {
    if (!this.schema || this.loading) {
      return html`<wa-spinner></wa-spinner>`;
    }
    
    // Get form layout from config or generate default
    const formSections = this.formConfig?.sections || [{
      title: this.itemId ? `Edit ${this.schema.displayName}` : `Create ${this.schema.displayName}`,
      fields: Object.entries(this.schema.properties)
        .filter(([_, prop]) => !prop.readOnly || this.itemId)
        .map(([name]) => name)
    }];
    
    return html`
      <div class="form-container">
        <form @submit=${this.handleSubmit}>
          ${formSections.map(section => html`
            <div class="form-section">
              ${section.title ? html`<wa-heading level="2">${section.title}</wa-heading>` : ''}
              
              <div class="form-fields">
                ${section.fields.map(field => this.renderField(field))}
              </div>
            </div>
          `)}
          
          <div class="form-actions">
            <wa-button 
              variant="default" 
              @click=${this.handleCancel}
              ?disabled=${this.saving}
            >
              Cancel
            </wa-button>
            
            <wa-button 
              variant="brand" 
              type="submit"
              ?loading=${this.saving}
            >
              ${this.itemId ? 'Update' : 'Create'} ${this.schema.displayName}
            </wa-button>
          </div>
        </form>
      </div>
    `;
  }
  
  renderField(fieldName) {
    const property = this.schema.properties[fieldName];
    if (!property) return null;
    
    // Check for relationship field
    const relationship = this.schema.relationships && this.schema.relationships[fieldName];
    if (relationship) {
      return this.renderRelationshipField(fieldName, property, relationship);
    }
    
    // Check for custom field renderer
    const resourceExtensions = extensions[this.resourceName] || {};
    const customRenderers = resourceExtensions.renderFields || {};
    
    if (customRenderers[fieldName]) {
      return customRenderers[fieldName](
        fieldName,
        property,
        this.formData[fieldName] || '',
        e => this.handleInputChange(fieldName, e),
        this.errors[fieldName]
      );
    }
    
    // Standard field rendering based on property type
    const value = this.formData[fieldName] ?? '';
    const error = this.errors[fieldName];
    const isReadOnly = property.readOnly;
    
    if (property.enum) {
      return html`
        <wa-select 
          label="${property.displayName || fieldName}"
          ?required=${property.required}
          ?disabled=${isReadOnly || this.saving}
          .value=${value}
          @wa-change=${e => this.handleInputChange(fieldName, e)}
          ?invalid=${!!error}
          error-text=${error || ''}
        >
          ${property.enum.map(option => html`
            <wa-option value="${option}">${option}</wa-option>
          `)}
        </wa-select>
      `;
    }
    
    if (property.type === 'boolean') {
      return html`
        <wa-checkbox
          ?checked=${value}
          ?disabled=${isReadOnly || this.saving}
          @wa-change=${e => this.handleInputChange(fieldName, e)}
        >
          ${property.displayName || fieldName}
        </wa-checkbox>
      `;
    }
    
    // More field types...
    
    // Default to text input
    return html`
      <wa-input
        type=${property.format === 'email' ? 'email' : 'text'}
        label="${property.displayName || fieldName}"
        ?required=${property.required}
        ?readonly=${isReadOnly}
        ?disabled=${this.saving}
        .value=${value}
        minlength=${property.minLength || ''}
        maxlength=${property.maxLength || ''}
        @wa-input=${e => this.handleInputChange(fieldName, e)}
        ?invalid=${!!error}
        error-text=${error || ''}
      ></wa-input>
    `;
  }
  
  async renderRelationshipField(fieldName, property, relationship) {
    // Implementation for relationship fields
    // ...
  }
  
  handleCancel() {
    this.dispatchEvent(new CustomEvent('navigate', {
      detail: { path: `/resources/${this.resourceName}` },
      bubbles: true,
      composed: true
    }));
  }
}

customElements.define('generic-form', GenericForm);
```

### Application Shell

The Application Shell ties everything together and handles routing:

```javascript
// app-shell.js
import { LitElement, html, css } from 'https://cdn.jsdelivr.net/npm/lit@2.8.0/+esm';
import { schemaService } from './services/schema-service.js';
import './components/resource-list.js';
import './components/generic-table.js';
import './components/generic-form.js';

class AppShell extends LitElement {
  static get properties() {
    return {
      route: { type: Object },
      resources: { type: Array },
      loading: { type: Boolean }
    };
  }
  
  constructor() {
    super();
    this.route = this.parseRoute();
    this.resources = [];
    this.loading = true;
    
    // Handle navigation events
    this.handleNavigate = this.handleNavigate.bind(this);
    
    // Handle browser navigation
    window.addEventListener('popstate', () => {
      this.route = this.parseRoute();
    });
  }
  
  async connectedCallback() {
    super.connectedCallback();
    
    // Load available resources
    try {
      this.resources = await schemaService.getResources();
    } catch (error) {
      console.error('Failed to load resources:', error);
    } finally {
      this.loading = false;
    }
    
    // Listen for navigation events
    this.addEventListener('navigate', this.handleNavigate);
  }
  
  disconnectedCallback() {
    super.disconnectedCallback();
    this.removeEventListener('navigate', this.handleNavigate);
  }
  
  parseRoute() {
    const path = window.location.pathname;
    const segments = path.split('/').filter(Boolean);
    
    if (segments.length === 0) {
      return { page: 'home' };
    }
    
    if (segments[0] === 'resources') {
      if (segments.length === 1) {
        return { page: 'resources' };
      }
      
      const resourceName = segments[1];
      
      if (segments.length === 2) {
        return { page: 'resourceList', resourceName };
      }
      
      if (segments[2] === 'create') {
        return { page: 'resourceCreate', resourceName };
      }
      
      if (segments[2] === 'edit' && segments.length === 4) {
        return { page: 'resourceEdit', resourceName, id: segments[3] };
      }
    }
    
    return { page: 'notFound' };
  }
  
  handleNavigate(e) {
    const { path } = e.detail;
    
    // Update browser history
    window.history.pushState(null, '', path);
    
    // Update route
    this.route = this.parseRoute();
  }
  
  render() {
    if (this.loading) {
      return html`<wa-spinner></wa-spinner>`;
    }
    
    return html`
      <wa-page>
        <header slot="header">
          <div class="header-content">
            <a href="/" class="logo" @click=${e => this.handleLinkClick(e, '/')}>
              <wa-icon name="server"></wa-icon>
              <wa-heading level="5">Admin Dashboard</wa-heading>
            </a>
            
            <nav>
              <wa-button @click=${e => this.handleLinkClick(e, '/')}>
                Home
              </wa-button>
              <wa-button @click=${e => this.handleLinkClick(e, '/resources')}>
                Resources
              </wa-button>
            </nav>
          </div>
        </header>
        
        <main slot="main">
          ${this.renderCurrentView()}
        </main>
        
        <footer slot="footer">
          <p>Generic Admin Interface - Powered by Schema Discovery</p>
        </footer>
      </wa-page>
    `;
  }
  
  renderCurrentView() {
    switch (this.route.page) {
      case 'home':
        return html`
          <div class="home-page">
            <wa-heading level="1">Admin Dashboard</wa-heading>
            <p>Welcome to the generic admin interface.</p>
            <wa-button 
              variant="brand" 
              size="large"
              @click=${e => this.handleLinkClick(e, '/resources')}
            >
              Browse Resources
            </wa-button>
          </div>
        `;
        
      case 'resources':
        return html`<resource-list></resource-list>`;
        
      case 'resourceList':
        return html`
          <generic-table 
            resourceName=${this.route.resourceName}
          ></generic-table>
        `;
        
      case 'resourceCreate':
        return html`
          <generic-form
            resourceName=${this.route.resourceName}
          ></generic-form>
        `;
        
      case 'resourceEdit':
        return html`
          <generic-form
            resourceName=${this.route.resourceName}
            itemId=${this.route.id}
          ></generic-form>
        `;
        
      case 'notFound':
      default:
        return html`
          <div class="not-found">
            <wa-heading level="1">Page Not Found</wa-heading>
            <p>The page you're looking for doesn't exist.</p>
            <wa-button @click=${e => this.handleLinkClick(e, '/')}>
              Go Home
            </wa-button>
          </div>
        `;
    }
  }
  
  handleLinkClick(e, path) {
    e.preventDefault();
    this.handleNavigate({ detail: { path } });
  }
}

customElements.define('app-shell', AppShell);
```

## WebAwesome 3.0 Integration

WebAwesome 3.0 provides powerful capabilities that make it particularly well-suited for schema-driven UIs. One of its most valuable features is the integration of the MutationObserver API, which enables the creation of reactive UIs that automatically respond to changes in the DOM.

### MutationObserver Pattern

The MutationObserver API is a browser feature that allows you to watch for changes in the DOM tree. WebAwesome 3.0 leverages this pattern to create a reactive UI system that can respond to both user interactions and server-side data changes.

#### Observer Component

Create a dedicated observer component that monitors DOM changes and reacts accordingly:

```javascript
// components/schema-observer.js
import { LitElement, html } from 'https://cdn.jsdelivr.net/npm/lit@2.8.0/+esm';
import { allDefined } from 'https://early.webawesome.com/webawesome@3.0.0-alpha.12/dist/webawesome.js';

class SchemaObserver extends LitElement {
  static get properties() {
    return {
      resourceName: { type: String },
      lastUpdate: { type: Number }
    };
  }
  
  constructor() {
    super();
    this.resourceName = '';
    this.lastUpdate = Date.now();
    this.observer = null;
  }
  
  connectedCallback() {
    super.connectedCallback();
    
    // Wait for WebAwesome components to be fully defined
    allDefined().then(() => {
      this.setupObserver();
    });
  }
  
  disconnectedCallback() {
    super.disconnectedCallback();
    
    // Clean up the observer to prevent memory leaks
    if (this.observer) {
      this.observer.disconnect();
      this.observer = null;
    }
  }
  
  setupObserver() {
    // Target the resource container to observe
    const targetSelector = `[data-resource="${this.resourceName}"]`;
    const targetElement = document.querySelector(targetSelector);
    
    if (!targetElement) {
      console.warn(`No element found for resource: ${this.resourceName}`);
      return;
    }
    
    // Create a configuration object
    const config = {
      attributes: true,      // Watch for attribute changes
      childList: true,       // Watch for child additions/removals
      subtree: true,         // Apply to all descendants
      attributeFilter: ['data-state', 'data-modified'] // Only specific attributes
    };
    
    // Create the observer with a callback
    this.observer = new MutationObserver((mutations) => {
      for (const mutation of mutations) {
        this.handleMutation(mutation);
      }
    });
    
    // Start observing
    this.observer.observe(targetElement, config);
    console.log(`Observer started for ${this.resourceName}`);
  }
  
  handleMutation(mutation) {
    // Update timestamp to trigger component re-render
    this.lastUpdate = Date.now();
    
    if (mutation.type === 'attributes') {
      const target = mutation.target;
      const attributeName = mutation.attributeName;
      const newValue = target.getAttribute(attributeName);
      const oldValue = mutation.oldValue;
      
      console.log(`Attribute changed: ${attributeName}`, {
        old: oldValue,
        new: newValue,
        element: target
      });
      
      // Handle specific attribute changes
      if (attributeName === 'data-state') {
        this.handleStateChange(target, oldValue, newValue);
      } else if (attributeName === 'data-modified') {
        this.handleModificationChange(target, oldValue, newValue);
      }
    } else if (mutation.type === 'childList') {
      if (mutation.addedNodes.length > 0) {
        console.log('Elements added:', mutation.addedNodes);
        this.handleAddedNodes(mutation.addedNodes);
      }
      
      if (mutation.removedNodes.length > 0) {
        console.log('Elements removed:', mutation.removedNodes);
        this.handleRemovedNodes(mutation.removedNodes);
      }
    }
    
    // Dispatch a custom event for other components to react to
    this.dispatchEvent(new CustomEvent('resource-changed', {
      bubbles: true,
      composed: true,
      detail: {
        resourceName: this.resourceName,
        mutation,
        timestamp: this.lastUpdate
      }
    }));
  }
  
  handleStateChange(element, oldState, newState) {
    // Handle element state changes
    if (newState === 'dirty') {
      // Element has unsaved changes
      this.highlightUnsavedChanges(element);
    } else if (newState === 'saving') {
      // Element is being saved
      this.showSavingIndicator(element);
    } else if (newState === 'saved') {
      // Element was successfully saved
      this.showSaveSuccess(element);
      
      // Reset state after a delay
      setTimeout(() => {
        element.setAttribute('data-state', 'clean');
      }, 3000);
    } else if (newState === 'error') {
      // Element encountered an error
      this.showSaveError(element);
    }
  }
  
  handleModificationChange(element, wasModified, isModified) {
    // Handle modification state changes
    if (isModified === 'true' && wasModified !== 'true') {
      // Element was just modified
      this.registerChange(element);
    }
  }
  
  handleAddedNodes(nodes) {
    // Process newly added nodes
    nodes.forEach(node => {
      if (node.nodeType === Node.ELEMENT_NODE) {
        // Initialize any newly added elements
        this.initializeElement(node);
        
        // Check for WebAwesome components
        if (node.nodeName.startsWith('WA-')) {
          console.log('WebAwesome component added:', node.nodeName);
          this.setupWebAwesomeComponent(node);
        }
      }
    });
  }
  
  handleRemovedNodes(nodes) {
    // Clean up removed nodes if necessary
    nodes.forEach(node => {
      if (node.nodeType === Node.ELEMENT_NODE) {
        // Clean up any resources or event listeners
        this.cleanupElement(node);
      }
    });
  }
  
  // Helper methods for visual feedback
  highlightUnsavedChanges(element) {
    // Add visual indicator for unsaved changes
    element.classList.add('has-unsaved-changes');
  }
  
  showSavingIndicator(element) {
    // Show saving indicator
    element.classList.add('is-saving');
    element.classList.remove('has-unsaved-changes', 'save-error');
  }
  
  showSaveSuccess(element) {
    // Show success indicator
    element.classList.add('save-success');
    element.classList.remove('is-saving', 'save-error');
  }
  
  showSaveError(element) {
    // Show error indicator
    element.classList.add('save-error');
    element.classList.remove('is-saving');
  }
  
  registerChange(element) {
    // Register a change that needs to be synced with the server
    const itemId = element.dataset.id;
    const field = element.dataset.field;
    const value = element.dataset.value || element.value || element.textContent;
    
    // Dispatch event for sync service to handle
    this.dispatchEvent(new CustomEvent('field-changed', {
      bubbles: true,
      composed: true,
      detail: { itemId, field, value, element }
    }));
  }
  
  initializeElement(element) {
    // Initialize a newly added element
    if (element.dataset.field) {
      // It's a field element, set up change tracking
      element.addEventListener('change', () => {
        element.setAttribute('data-modified', 'true');
        element.setAttribute('data-state', 'dirty');
      });
    }
  }
  
  setupWebAwesomeComponent(element) {
    // Add specific setup for WebAwesome components
    element.addEventListener('wa-change', () => {
      element.setAttribute('data-modified', 'true');
      element.setAttribute('data-state', 'dirty');
    });
  }
  
  cleanupElement(element) {
    // Clean up resources associated with an element
    // No implementation needed for this example
  }
  
  render() {
    // This component doesn't render any visible UI
    return html``;
  }
}

customElements.define('schema-observer', SchemaObserver);
```

### Reactive UI Updates

Use the MutationObserver pattern to create reactive UI components that automatically update when schema data changes:

```javascript
// components/reactive-resource-view.js
import { LitElement, html, css } from 'https://cdn.jsdelivr.net/npm/lit@2.8.0/+esm';
import { schemaService } from '../services/schema-service.js';
import './schema-observer.js';

class ReactiveResourceView extends LitElement {
  static get properties() {
    return {
      resourceName: { type: String },
      items: { type: Array },
      schema: { type: Object },
      loading: { type: Boolean },
      lastUpdate: { type: Number }
    };
  }
  
  constructor() {
    super();
    this.resourceName = '';
    this.items = [];
    this.schema = null;
    this.loading = true;
    this.lastUpdate = Date.now();
    
    // Bind event handlers
    this.handleResourceChanged = this.handleResourceChanged.bind(this);
    this.handleFieldChanged = this.handleFieldChanged.bind(this);
  }
  
  connectedCallback() {
    super.connectedCallback();
    
    // Load initial data
    this.loadSchemaAndData();
    
    // Listen for change events
    this.addEventListener('resource-changed', this.handleResourceChanged);
    this.addEventListener('field-changed', this.handleFieldChanged);
  }
  
  disconnectedCallback() {
    super.disconnectedCallback();
    
    // Clean up event listeners
    this.removeEventListener('resource-changed', this.handleResourceChanged);
    this.removeEventListener('field-changed', this.handleFieldChanged);
  }
  
  async loadSchemaAndData() {
    this.loading = true;
    
    try {
      // Load schema first
      this.schema = await schemaService.getSchema(this.resourceName);
      
      // Then load data
      await this.loadItems();
    } catch (error) {
      console.error(`Failed to load schema or data for ${this.resourceName}:`, error);
    } finally {
      this.loading = false;
    }
  }
  
  async loadItems() {
    try {
      const endpoint = this.schema.endpoints.list;
      const response = await fetch(endpoint);
      this.items = await response.json();
      
      // Update the timestamp to trigger a re-render
      this.lastUpdate = Date.now();
    } catch (error) {
      console.error(`Failed to load items for ${this.resourceName}:`, error);
    }
  }
  
  handleResourceChanged(event) {
    // When resource changes, check if we need to refresh data
    const { resourceName, mutation } = event.detail;
    
    // Only process if it's for our resource
    if (resourceName !== this.resourceName) return;
    
    // If a significant change happened, reload data
    if (mutation.type === 'childList' || 
        (mutation.type === 'attributes' && 
         mutation.attributeName === 'data-state' && 
         mutation.target.getAttribute('data-state') === 'saved')) {
      this.loadItems();
    }
  }
  
  async handleFieldChanged(event) {
    const { itemId, field, value } = event.detail;
    
    // Mark the element as saving
    const element = event.detail.element;
    element.setAttribute('data-state', 'saving');
    
    try {
      // Find the endpoint for updating this resource
      const endpoint = this.schema.endpoints.update.replace('{id}', itemId);
      
      // Create payload with just the changed field
      const payload = { [field]: value };
      
      // Send update to server
      const response = await fetch(endpoint, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      
      if (!response.ok) {
        throw new Error('Failed to update resource');
      }
      
      // Mark as saved
      element.setAttribute('data-state', 'saved');
      
      // Update local data
      const updatedItem = await response.json();
      this.updateLocalItem(itemId, updatedItem);
    } catch (error) {
      console.error('Error updating resource:', error);
      
      // Mark as error
      element.setAttribute('data-state', 'error');
    }
  }
  
  updateLocalItem(itemId, updatedItem) {
    // Update the local items array
    const index = this.items.findIndex(item => item[this.schema.primaryKey] === itemId);
    
    if (index !== -1) {
      this.items = [
        ...this.items.slice(0, index),
        updatedItem,
        ...this.items.slice(index + 1)
      ];
    }
  }
  
  render() {
    if (this.loading) {
      return html`<wa-spinner></wa-spinner>`;
    }
    
    if (!this.schema) {
      return html`<wa-callout variant="danger">Failed to load schema</wa-callout>`;
    }
    
    return html`
      <div class="resource-view" data-resource="${this.resourceName}">
        <wa-heading level="2">${this.schema.displayName}</wa-heading>
        
        <div class="resource-items">
          ${this.items.map(item => this.renderItem(item))}
        </div>
        
        <!-- Observer component to watch for changes -->
        <schema-observer 
          resourceName="${this.resourceName}"
        ></schema-observer>
      </div>
    `;
  }
  
  renderItem(item) {
    const id = item[this.schema.primaryKey];
    
    return html`
      <div class="resource-item" data-id="${id}">
        <wa-heading level="3">${item[this.schema.displayField]}</wa-heading>
        
        <div class="resource-fields">
          ${Object.entries(this.schema.properties)
            .filter(([name, prop]) => !prop.hidden)
            .map(([name, prop]) => this.renderField(name, prop, item[name], id))}
        </div>
      </div>
    `;
  }
  
  renderField(name, property, value, itemId) {
    // Skip the primary key and display field in the detail view
    if (name === this.schema.primaryKey || name === this.schema.displayField) {
      return null;
    }
    
    if (property.readOnly) {
      // Read-only field
      return html`
        <div class="field-container">
          <label>${property.displayName || name}</label>
          <div class="field-value">${this.formatValue(value, property)}</div>
        </div>
      `;
    }
    
    // Editable field
    return html`
      <div class="field-container">
        <label>${property.displayName || name}</label>
        <wa-input
          .value=${value || ''}
          data-id="${itemId}"
          data-field="${name}"
          @wa-change=${this.handleInputChange}
        ></wa-input>
      </div>
    `;
  }
  
  formatValue(value, property) {
    if (value === null || value === undefined) {
      return '-';
    }
    
    if (property.format === 'date-time') {
      return new Date(value).toLocaleString();
    }
    
    if (property.type === 'boolean') {
      return value ? 'Yes' : 'No';
    }
    
    return value.toString();
  }
  
  handleInputChange(e) {
    const target = e.target;
    target.setAttribute('data-modified', 'true');
    target.setAttribute('data-state', 'dirty');
    target.setAttribute('data-value', target.value);
  }
}

customElements.define('reactive-resource-view', ReactiveResourceView);
```

### Real-time Synchronization

Combine MutationObserver with WebSockets to create a real-time synchronized UI:

```javascript
// services/sync-service.js
export class SyncService {
  constructor(resourceName) {
    this.resourceName = resourceName;
    this.socket = null;
    this.pendingChanges = new Map();
    this.isConnected = false;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
    this.reconnectDelay = 1000;
  }
  
  connect() {
    // Connect to WebSocket server
    this.socket = new WebSocket(`wss://api.example.com/sync/${this.resourceName}`);
    
    this.socket.addEventListener('open', () => {
      console.log(`WebSocket connected for ${this.resourceName}`);
      this.isConnected = true;
      this.reconnectAttempts = 0;
      
      // Process any pending changes
      this.processPendingChanges();
    });
    
    this.socket.addEventListener('message', (event) => {
      try {
        const data = JSON.parse(event.data);
        this.handleServerMessage(data);
      } catch (error) {
        console.error('Error processing WebSocket message:', error);
      }
    });
    
    this.socket.addEventListener('close', () => {
      this.isConnected = false;
      console.log(`WebSocket disconnected for ${this.resourceName}`);
      
      // Attempt to reconnect
      this.attemptReconnect();
    });
    
    this.socket.addEventListener('error', (error) => {
      console.error('WebSocket error:', error);
    });
  }
  
  attemptReconnect() {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);
      
      console.log(`Attempting to reconnect in ${delay}ms (attempt ${this.reconnectAttempts})`);
      
      setTimeout(() => {
        this.connect();
      }, delay);
    } else {
      console.error('Max reconnect attempts reached. Giving up.');
    }
  }
  
  registerChange(itemId, field, value) {
    // Create a change record
    const changeKey = `${itemId}:${field}`;
    const changeRecord = { itemId, field, value, timestamp: Date.now() };
    
    // Store in pending changes
    this.pendingChanges.set(changeKey, changeRecord);
    
    // Try to send immediately if connected
    if (this.isConnected) {
      this.processPendingChanges();
    }
    
    return changeRecord;
  }
  
  processPendingChanges() {
    if (!this.isConnected || this.pendingChanges.size === 0) return;
    
    // Process all pending changes
    for (const [key, change] of this.pendingChanges.entries()) {
      this.sendChange(change).then(() => {
        // Remove from pending changes on success
        this.pendingChanges.delete(key);
      }).catch(error => {
        console.error('Failed to send change:', error);
        // Keep in pending changes to try again later
      });
    }
  }
  
  async sendChange(change) {
    return new Promise((resolve, reject) => {
      // Create a message
      const message = {
        type: 'change',
        resource: this.resourceName,
        ...change
      };
      
      // Send via WebSocket
      try {
        this.socket.send(JSON.stringify(message));
        resolve();
      } catch (error) {
        reject(error);
      }
    });
  }
  
  handleServerMessage(message) {
    if (message.type === 'change') {
      // Server is notifying about a change
      const { itemId, field, value } = message;
      
      // Find elements that need to be updated
      const selector = `[data-id="${itemId}"][data-field="${field}"]`;
      document.querySelectorAll(selector).forEach(element => {
        // Update the element value
        if (element.tagName === 'WA-INPUT') {
          element.value = value;
        } else {
          element.textContent = value;
        }
        
        // Update data attributes
        element.setAttribute('data-value', value);
        
        // Dispatch an event for the mutation observer to detect
        element.dispatchEvent(new CustomEvent('server-update', {
          bubbles: true,
          composed: true,
          detail: { itemId, field, value }
        }));
      });
    } else if (message.type === 'refresh') {
      // Server is requesting a full refresh
      document.dispatchEvent(new CustomEvent('refresh-resource', {
        bubbles: true,
        detail: { resourceName: this.resourceName }
      }));
    }
  }
  
  disconnect() {
    if (this.socket) {
      this.socket.close();
      this.socket = null;
    }
  }
}
```

To integrate this sync service with the observer pattern, add the following component:

```javascript
// components/sync-observer.js
import { LitElement, html } from 'https://cdn.jsdelivr.net/npm/lit@2.8.0/+esm';
import { SyncService } from '../services/sync-service.js';

class SyncObserver extends LitElement {
  static get properties() {
    return {
      resourceName: { type: String },
      autoConnect: { type: Boolean }
    };
  }
  
  constructor() {
    super();
    this.resourceName = '';
    this.autoConnect = true;
    this.syncService = null;
  }
  
  connectedCallback() {
    super.connectedCallback();
    
    if (this.resourceName && this.autoConnect) {
      this.initializeSyncService();
    }
    
    // Listen for field changes
    this.addEventListener('field-changed', this.handleFieldChanged.bind(this));
    
    // Listen for refresh requests
    document.addEventListener('refresh-resource', this.handleRefreshRequest.bind(this));
  }
  
  disconnectedCallback() {
    super.disconnectedCallback();
    
    // Clean up
    this.removeEventListener('field-changed', this.handleFieldChanged.bind(this));
    document.removeEventListener('refresh-resource', this.handleRefreshRequest.bind(this));
    
    if (this.syncService) {
      this.syncService.disconnect();
    }
  }
  
  initializeSyncService() {
    this.syncService = new SyncService(this.resourceName);
    this.syncService.connect();
  }
  
  handleFieldChanged(event) {
    // Only process if it's for our resource
    if (event.detail.element.closest(`[data-resource="${this.resourceName}"]`)) {
      const { itemId, field, value } = event.detail;
      
      if (this.syncService) {
        this.syncService.registerChange(itemId, field, value);
      }
    }
  }
  
  handleRefreshRequest(event) {
    // Only process if it's for our resource
    if (event.detail.resourceName === this.resourceName) {
      // Dispatch a custom event to trigger a refresh
      this.dispatchEvent(new CustomEvent('refresh-needed', {
        bubbles: true,
        composed: true,
        detail: { resourceName: this.resourceName }
      }));
    }
  }
  
  render() {
    // This component doesn't render any visible UI
    return html``;
  }
}

customElements.define('sync-observer', SyncObserver);
```

Finally, use both observers in your reactive resource view:

```javascript
// In your reactive-resource-view.js render method
render() {
  // ... existing render code ...
  
  return html`
    <div class="resource-view" data-resource="${this.resourceName}">
      <!-- Existing content -->
      
      <!-- Observer components to watch for changes -->
      <schema-observer 
        resourceName="${this.resourceName}"
      ></schema-observer>
      
      <sync-observer
        resourceName="${this.resourceName}"
        @refresh-needed=${() => this.loadItems()}
      ></sync-observer>
    </div>
  `;
}
```

This implementation creates a powerful, reactive UI that:

1. Monitors the DOM for changes using MutationObserver
2. Automatically synchronizes local changes with the server
3. Updates the UI in real-time when changes occur, either locally or from the server
4. Provides visual feedback during the synchronization process
5. Handles reconnection and error states gracefully

### Extension Service

```javascript
// custom-extensions.js
import { html } from 'https://cdn.jsdelivr.net/npm/lit@2.8.0/+esm';

export const extensions = {
  // Custom extensions for the 'users' resource
  users: {
    // Custom action handlers
    actions: {
      resetPassword: async (userId) => {
        // Custom implementation for reset password
        console.log('Custom reset password for user', userId);
        
        // Call the API
        const response = await fetch(`/api/users/${userId}/reset-password`, {
          method: 'POST'
        });
        
        return response.json();
      }
    },
    
    // Custom form field renderers
    renderFields: {
      password: (fieldName, property, value, onChange, error) => {
        return html`
          <div class="password-field">
            <wa-input
              type="password"
              label="${property.displayName || fieldName}"
              ?required=${property.required}
              .value=${value}
              @wa-input=${onChange}
              ?invalid=${!!error}
              error-text=${error || ''}
            ></wa-input>
            <wa-button size="small" type="button">Generate</wa-button>
          </div>
        `;
      }
    },
    
    // Custom validation logic
    validate: (formData, schema) => {
      const errors = {};
      
      // Custom validation for password fields
      if (formData.password && formData.password.length < 8) {
        errors.password = 'Password must be at least 8 characters long';
      }
      
      if (formData.password && formData.passwordConfirm && 
          formData.password !== formData.passwordConfirm) {
        errors.passwordConfirm = 'Passwords do not match';
      }
      
      return errors;
    }
  },
  
  // Custom extensions for the 'products' resource
  products: {
    renderFields: {
      // Custom image uploader field
      imageUrl: (fieldName, property, value, onChange, error) => {
        return html`
          <div class="image-upload-field">
            <label>${property.displayName || fieldName}</label>
            
            ${value ? html`
              <img src="${value}" alt="Product Image" class="preview-image">
            ` : ''}
            
            <wa-button type="button" @click=${() => openImageUploadDialog(onChange)}>
              ${value ? 'Change Image' : 'Upload Image'}
            </wa-button>
            
            ${error ? html`<div class="error">${error}</div>` : ''}
          </div>
        `;
      }
    },
    
    // Custom table cell renderers
    renderCells: {
      imageUrl: (value, item) => {
        return html`
          <div class="image-cell">
            <img src="${value}" alt="${item.name}" width="50" height="50">
          </div>
        `;
      },
      price: (value) => {
        return html`
          <div class="price-cell">
            <strong>${parseFloat(value).toFixed(2)}</strong>
          </div>
        `;
      }
    }
  }
};

// Helper functions for extensions
function openImageUploadDialog(onChange) {
  // Create a file input
  const input = document.createElement('input');
  input.type = 'file';
  input.accept = 'image/*';
  
  input.onchange = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    
    // In a real app, upload the file to your server
    // Here we're just creating a data URL for demo purposes
    const reader = new FileReader();
    reader.onload = () => {
      onChange({ target: { value: reader.result } });
    };
    reader.readAsDataURL(file);
  };
  
  // Trigger the file dialog
  input.click();
}
```

## Advanced Features

### Relationship Handling

One of the most important features of a generic UI system is handling relationships between resources:

```javascript
async renderRelationshipField(fieldName, property, relationship) {
  // Load related resource schema and data
  const relatedSchema = await schemaService.getSchema(relationship.resource);
  
  if (relationship.type === 'belongsTo') {
    // For a belongsTo relationship, show a dropdown
    const foreignKey = relationship.foreignKey || `${fieldName}Id`;
    const selectedValue = this.formData[foreignKey] || '';
    
    // Load options
    const response = await fetch(relatedSchema.endpoints.list);
    const options = await response.json();
    
    return html`
      <wa-select
        label="${property.displayName || fieldName}"
        ?required=${property.required}
        ?disabled=${this.saving}
        .value=${selectedValue}
        @wa-change=${e => this.handleInputChange(foreignKey, e)}
        ?invalid=${!!this.errors[foreignKey]}
        error-text=${this.errors[foreignKey] || ''}
      >
        <wa-option value="">-- Select ${relatedSchema.displayName} --</wa-option>
        ${options.map(option => html`
          <wa-option value="${option[relatedSchema.primaryKey]}">
            ${option[relatedSchema.displayField]}
          </wa-option>
        `)}
      </wa-select>
    `;
  }
  
  if (relationship.type === 'hasMany') {
    // For a hasMany relationship, show a multi-select or a list with add/remove
    const selectedIds = this.formData[`${fieldName}Ids`] || [];
    
    // Load options
    const response = await fetch(relatedSchema.endpoints.list);
    const options = await response.json();
    
    return html`
      <div class="related-items">
        <label>${property.displayName || fieldName}</label>
        
        <wa-multi-select
          ?disabled=${this.saving}
          @wa-change=${e => this.handleRelatedItemsChange(fieldName, e)}
          ?invalid=${!!this.errors[`${fieldName}Ids`]}
          error-text=${this.errors[`${fieldName}Ids`] || ''}
        >
          ${options.map(option => html`
            <wa-option 
              value="${option[relatedSchema.primaryKey]}"
              ?selected=${selectedIds.includes(option[relatedSchema.primaryKey])}
            >
              ${option[relatedSchema.displayField]}
            </wa-option>
          `)}
        </wa-multi-select>
      </div>
    `;
  }
  
  return null;
}
```

### Filtering and Searching

Adding search and filter capabilities is essential for tables with many rows:

```javascript
// Inside the GenericTable class
async loadItems() {
  this.loading = true;
  
  try {
    // Build the query string with pagination, sorting, etc.
    const params = new URLSearchParams({
      _page: this.page.toString(),
      _limit: this.pageSize.toString()
    });
    
    if (this.sortField) {
      const sortPrefix = this.sortDirection === 'desc' ? '-' : '';
      params.append('_sort', `${sortPrefix}${this.sortField}`);
    }
    
    // Add search term if present
    if (this.searchTerm) {
      params.append('q', this.searchTerm);
    }
    
    // Add filters
    Object.entries(this.filters).forEach(([key, value]) => {
      if (value !== null && value !== undefined && value !== '') {
        params.append(key, value);
      }
    });
    
    const endpoint = this.schema.endpoints.list;
    const response = await fetch(`${endpoint}?${params.toString()}`);
    
    // Handle pagination headers
    const totalItems = response.headers.get('X-Total-Count');
    if (totalItems) {
      this.totalItems = parseInt(totalItems, 10);
    }
    
    this.items = await response.json();
  } catch (error) {
    console.error(`Failed to load items for ${this.resourceName}:`, error);
  } finally {
    this.loading = false;
  }
}
```

### Bulk Operations

For efficiency, enable bulk operations on multiple selected items:

```javascript
// Inside the GenericTable class
async handleBulkAction(action) {
  if (this.selectedItems.size === 0) {
    this.dispatchEvent(new CustomEvent('show-toast', {
      detail: { message: 'No items selected', variant: 'warning' },
      bubbles: true,
      composed: true
    }));
    return;
  }
  
  if (!confirm(`Are you sure you want to ${action} the selected items?`)) {
    return;
  }
  
  try {
    if (action === 'delete') {
      await Promise.all(
        Array.from(this.selectedItems).map(id => {
          const endpoint = this.schema.endpoints.delete.replace('{id}', id);
          return fetch(endpoint, { method: 'DELETE' });
        })
      );
    } else if (this.schema.bulkActions && this.schema.bulkActions[action]) {
      const bulkAction = this.schema.bulkActions[action];
      await fetch(bulkAction.endpoint, {
        method: bulkAction.method || 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ids: Array.from(this.selectedItems)
        })
      });
    }
    
    // Reload the table
    this.loadItems();
    
    // Clear selection
    this.selectedItems.clear();
    
    // Show success message
    this.dispatchEvent(new CustomEvent('show-toast', {
      detail: { message: 'Bulk action completed successfully', variant: 'success' },
      bubbles: true,
      composed: true
    }));
  } catch (error) {
    console.error(`Failed to execute bulk action:`, error);
    
    this.dispatchEvent(new CustomEvent('show-toast', {
      detail: { message: `Failed to complete bulk action: ${error.message}`, variant: 'danger' },
      bubbles: true,
      composed: true
    }));
  }
}
```

## Best Practices

### 1. Schema Design

- **Be consistent with property types**: Use the same data types for similar fields across resources
- **Include meaningful display names**: Don't rely on field names for UI display
- **Use enums for fixed value sets**: Define allowed values for fields with a fixed set of options
- **Document relationships clearly**: Include all necessary information for relationship handling
- **Provide sensible defaults**: Set default values where appropriate to improve UX

### 2. Performance Optimization

- **Cache schemas**: Store schemas in memory to avoid repeated requests
- **Use pagination**: Always paginate large collections
- **Implement virtual scrolling**: For very large tables, consider virtual scrolling
- **Lazy load related resources**: Only fetch related data when needed
- **Use JSON schema $ref for shared definitions**: Avoid duplication in your schemas

### 3. Security Considerations

- **Include permissions in schema**: Define what operations are allowed for each resource
- **Validate inputs on both client and server**: Never trust client-side validation alone
- **Use HTTPS for all API calls**: Secure data in transit
- **Implement proper authentication**: Include authentication tokens in requests
- **Respect CORS headers**: Set up proper cross-origin resource sharing

### 4. Extensibility

- **Design for composition**: Make components composable and reusable
- **Use the extension system**: Avoid modifying core components directly
- **Keep extensions resource-specific**: Organize extensions by resource name
- **Document extension points**: Make it clear how to extend components

### 5. Accessibility

- **Use proper ARIA attributes**: Make generic UI accessible
- **Test with screen readers**: Verify accessibility with real assistive technologies
- **Support keyboard navigation**: Ensure all functionality works with keyboard
- **Follow color contrast guidelines**: Make sure text is readable
- **Provide text alternatives**: Always include alt text for images

### 6. MutationObserver Best Practices

- **Be selective with observers**: Only observe elements that need observation to avoid performance issues
- **Use attribute filters**: Specify which attributes to watch rather than observing all changes
- **Clean up observers**: Always disconnect observers when components are removed
- **Batch DOM updates**: Group related updates to reduce the number of mutations
- **Use debouncing**: Debounce mutation handlers for performance-intensive operations
- **Use data attributes for state**: Store state in data attributes to make it observable
- **Structure event handling**: Create a clean system of custom events for mutations
- **Use requestAnimationFrame**: Defer UI updates to the next paint cycle for smoother animations**: Make sure text is readable
- **Provide text alternatives**: Always include alt text for images

## Example Implementation

Here's how to set up a complete implementation of this system with WebAwesome 3.0 and MutationObserver integration:

### 1. Project Structure

```
schema-driven-ui/
├── index.html                # Main HTML file
├── components/               # Web components
│   ├── resource-list.js      # List available resources
│   ├── generic-table.js      # Display and manage resource collections
│   ├── generic-form.js       # Create and edit resource instances
│   ├── schema-observer.js    # MutationObserver component
│   ├── sync-observer.js      # WebSocket synchronization
│   ├── reactive-resource-view.js # Reactive resource view
│   └── app-shell.js          # Main application component
├── services/                 # Service layer
│   ├── schema-service.js     # Fetch and process schemas
│   ├── sync-service.js       # Real-time synchronization
│   └── custom-extensions.js  # Custom behaviors for specific resources
└── styles/                   # Optional global styles
    └── main.css              # Global CSS
```

### 2. HTML Entry Point

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Schema-Driven Admin Dashboard</title>
  
  <!-- WebAwesome 3.0 -->
  <link rel="stylesheet" href="https://early.webawesome.com/webawesome@3.0.0-alpha.12/dist/styles/themes/default.css" />
  <link rel="stylesheet" href="https://early.webawesome.com/webawesome@3.0.0-alpha.12/dist/styles/webawesome.css" />
  <script type="module" src="https://early.webawesome.com/webawesome@3.0.0-alpha.12/dist/webawesome.loader.js"></script>
  
  <!-- Lit Library -->
  <script type="module" src="https://cdn.jsdelivr.net/npm/lit@2.8.0/+esm"></script>
  
  <!-- Application components -->
  <script type="module" src="./components/app-shell.js"></script>
  
  <!-- Global styles -->
  <link rel="stylesheet" href="./styles/main.css">
  
  <style>
    /* Animation styles for mutation feedback */
    @keyframes highlight {
      0% { background-color: transparent; }
      30% { background-color: rgba(var(--wa-color-brand-fill-loud-rgb), 0.3); }
      100% { background-color: transparent; }
    }
    
    [data-state="dirty"] {
      border-left: 3px solid var(--wa-color-warning-fill-loud);
    }
    
    [data-state="saving"] {
      border-left: 3px solid var(--wa-color-info-fill-loud);
      opacity: 0.8;
    }
    
    [data-state="saved"] {
      border-left: 3px solid var(--wa-color-success-fill-loud);
      animation: highlight 2s ease-in-out;
    }
    
    [data-state="error"] {
      border-left: 3px solid var(--wa-color-danger-fill-loud);
    }
  </style>
</head>
<body>
  <app-shell></app-shell>
</body>
</html>
```

### 3. Enhanced App Shell With Observer Integration

Update the app-shell to integrate the observer components:

```javascript
// components/app-shell.js
import { LitElement, html, css } from 'https://cdn.jsdelivr.net/npm/lit@2.8.0/+esm';
import { allDefined } from 'https://early.webawesome.com/webawesome@3.0.0-alpha.12/dist/webawesome.js';
import { schemaService } from '../services/schema-service.js';

// Import standard components
import './resource-list.js';
import './generic-table.js';
import './generic-form.js';

// Import observer components
import './schema-observer.js';
import './sync-observer.js';
import './reactive-resource-view.js';

class AppShell extends LitElement {
  static get properties() {
    return {
      route: { type: Object },
      resources: { type: Array },
      loading: { type: Boolean },
      initialized: { type: Boolean }
    };
  }
  
  static get styles() {
    return css`
      :host {
        display: block;
        min-height: 100vh;
      }
      
      .header-content {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: var(--wa-space-s);
      }
      
      .logo {
        display: flex;
        align-items: center;
        gap: var(--wa-space-xs);
        color: var(--wa-color-brand-fill-loud);
        text-decoration: none;
      }
      
      .toast-container {
        position: fixed;
        bottom: 20px;
        right: 20px;
        z-index: 1000;
      }
      
      .toast {
        margin-bottom: 10px;
        animation: fadeIn 0.3s, fadeOut 0.3s 2.7s;
      }
      
      @keyframes fadeIn {
        from { opacity: 0; transform: translateY(20px); }
        to { opacity: 1; transform: translateY(0); }
      }
      
      @keyframes fadeOut {
        from { opacity: 1; transform: translateY(0); }
        to { opacity: 0; transform: translateY(20px); }
      }
    `;
  }
  
  constructor() {
    super();
    this.route = this.parseRoute();
    this.resources = [];
    this.loading = true;
    this.initialized = false;
    this.toasts = [];
    this.toastCounter = 0;
    
    // Handle navigation events
    this.handleNavigate = this.handleNavigate.bind(this);
    this.handleShowToast = this.handleShowToast.bind(this);
    
    // Handle browser navigation
    window.addEventListener('popstate', () => {
      this.route = this.parseRoute();
    });
  }
  
  async connectedCallback() {
    super.connectedCallback();
    
    // Wait for WebAwesome components to be defined
    try {
      await allDefined();
      console.log('All WebAwesome components are ready!');
      this.initialized = true;
    } catch (error) {
      console.error('Error initializing WebAwesome components:', error);
    }
    
    // Load available resources
    try {
      this.resources = await schemaService.getResources();
    } catch (error) {
      console.error('Failed to load resources:', error);
      this.handleShowToast({
        detail: { 
          message: 'Failed to load resources', 
          variant: 'danger' 
        }
      });
    } finally {
      this.loading = false;
    }
    
    // Listen for navigation events
    this.addEventListener('navigate', this.handleNavigate);
    
    // Listen for toast notifications
    window.addEventListener('show-toast', this.handleShowToast);
    
    // Listen for mutation observer events
    window.addEventListener('resource-changed', (e) => {
      console.log('Resource changed:', e.detail);
    });
  }
  
  disconnectedCallback() {
    super.disconnectedCallback();
    this.removeEventListener('navigate', this.handleNavigate);
    window.removeEventListener('show-toast', this.handleShowToast);
    window.removeEventListener('resource-changed', () => {});
  }
  
  parseRoute() {
    const path = window.location.pathname;
    const segments = path.split('/').filter(Boolean);
    
    if (segments.length === 0) {
      return { page: 'home' };
    }
    
    if (segments[0] === 'resources') {
      if (segments.length === 1) {
        return { page: 'resources' };
      }
      
      const resourceName = segments[1];
      
      if (segments.length === 2) {
        // Support both standard and reactive views
        if (path.includes('reactive')) {
          return { page: 'reactiveResource', resourceName };
        } else {
          return { page: 'resourceList', resourceName };
        }
      }
      
      if (segments[2] === 'create') {
        return { page: 'resourceCreate', resourceName };
      }
      
      if (segments[2] === 'edit' && segments.length === 4) {
        return { page: 'resourceEdit', resourceName, id: segments[3] };
      }
    }
    
    return { page: 'notFound' };
  }
  
  handleNavigate(e) {
    const { path } = e.detail;
    
    // Update browser history
    window.history.pushState(null, '', path);
    
    // Update route
    this.route = this.parseRoute();
  }
  
  handleShowToast(e) {
    const { message, variant = 'info', duration = 3000 } = e.detail;
    
    // Create toast
    const toast = {
      id: this.toastCounter++,
      message,
      variant,
      duration
    };
    
    // Add to toasts array
    this.toasts = [...this.toasts, toast];
    
    // Schedule toast removal
    setTimeout(() => {
      this.toasts = this.toasts.filter(t => t.id !== toast.id);
    }, toast.duration);
    
    // Force update
    this.requestUpdate();
  }
  
  render() {
    if (!this.initialized || this.loading) {
      return html`
        <div class="loading-container" style="display: flex; justify-content: center; align-items: center; height: 100vh;">
          <wa-spinner size="large"></wa-spinner>
        </div>
      `;
    }
    
    return html`
      <wa-page>
        <header slot="header">
          <div class="header-content">
            <a href="/" class="logo" @click=${e => this.handleLinkClick(e, '/')}>
              <wa-icon name="server"></wa-icon>
              <wa-heading level="5">Schema-Driven UI</wa-heading>
            </a>
            
            <nav>
              <wa-button @click=${e => this.handleLinkClick(e, '/')}>
                Home
              </wa-button>
              <wa-button @click=${e => this.handleLinkClick(e, '/resources')}>
                Resources
              </wa-button>
            </nav>
          </div>
        </header>
        
        <main slot="main">
          ${this.renderCurrentView()}
        </main>
        
        <footer slot="footer">
          <p>Schema-Driven UI with WebAwesome 3.0 • Powered by MutationObserver</p>
        </footer>
      </wa-page>
      
      <!-- Toast notifications -->
      <div class="toast-container">
        ${this.toasts.map(toast => html`
          <wa-callout 
            class="toast"
            variant="${toast.variant}"
          >
            ${toast.message}
          </wa-callout>
        `)}
      </div>
    `;
  }
  
  renderCurrentView() {
    if (!this.initialized) {
      return html`<wa-spinner></wa-spinner>`;
    }
    
    switch (this.route.page) {
      case 'home':
        return html`
          <div class="home-page">
            <wa-heading level="1">Schema-Driven Admin Dashboard</wa-heading>
            <p>Welcome to the schema-driven UI interface with reactive updates powered by WebAwesome 3.0.</p>
            
            <div style="display: flex; gap: var(--wa-space-m); margin-top: var(--wa-space-l);">
              <wa-button 
                variant="brand" 
                size="large"
                @click=${e => this.handleLinkClick(e, '/resources')}
              >
                Browse Resources
              </wa-button>
              
              <wa-button 
                variant="default" 
                size="large"
                @click=${() => window.open('https://backers.webawesome.com/docs/', '_blank')}
              >
                WebAwesome Docs
              </wa-button>
            </div>
          </div>
        `;
        
      case 'resources':
        return html`<resource-list></resource-list>`;
        
      case 'resourceList':
        return html`
          <generic-table 
            resourceName=${this.route.resourceName}
          ></generic-table>
        `;
        
      case 'reactiveResource':
        return html`
          <reactive-resource-view
            resourceName=${this.route.resourceName}
          ></reactive-resource-view>
        `;
        
      case 'resourceCreate':
        return html`
          <generic-form
            resourceName=${this.route.resourceName}
          ></generic-form>
        `;
        
      case 'resourceEdit':
        return html`
          <generic-form
            resourceName=${this.route.resourceName}
            itemId=${this.route.id}
          ></generic-form>
        `;
        
      case 'notFound':
      default:
        return html`
          <div class="not-found">
            <wa-heading level="1">Page Not Found</wa-heading>
            <p>The page you're looking for doesn't exist.</p>
            <wa-button @click=${e => this.handleLinkClick(e, '/')}>
              Go Home
            </wa-button>
          </div>
        `;
    }
  }
  
  handleLinkClick(e, path) {
    e.preventDefault();
    this.handleNavigate({ detail: { path } });
  }
}

customElements.define('app-shell', AppShell);
```

### 4. Enhanced Resource List With Reactive Options

Add reactive viewing options to the resource list:

```javascript
// components/resource-list.js
// Inside the renderResourceCard method

renderResourceCard(resource) {
  return html`
    <wa-card>
      <wa-heading level="3">${resource.displayName}</wa-heading>
      <p>${resource.description}</p>
      
      <div class="card-actions" style="display: flex; gap: var(--wa-space-xs); margin-top: var(--wa-space-m);">
        <wa-button @click=${() => this.navigateToResource(resource.name)}>
          Standard View
        </wa-button>
        
        <wa-button 
          variant="brand" 
          @click=${() => this.navigateToReactiveResource(resource.name)}
        >
          Reactive View
        </wa-button>
      </div>
    </wa-card>
  `;
}

navigateToResource(resourceName) {
  const event = new CustomEvent('navigate', {
    detail: { path: `/resources/${resourceName}` },
    bubbles: true,
    composed: true
  });
  this.dispatchEvent(event);
}

navigateToReactiveResource(resourceName) {
  const event = new CustomEvent('navigate', {
    detail: { path: `/resources/${resourceName}/reactive` },
    bubbles: true,
    composed: true
  });
  this.dispatchEvent(event);
}
```

### 5. Global CSS for Mutation Indicators

Add styles to visually indicate mutations:

```css
/* styles/main.css */
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

/* Animation styles for mutation feedback */
@keyframes highlight {
  0% { background-color: transparent; }
  30% { background-color: rgba(var(--wa-color-brand-fill-loud-rgb), 0.3); }
  100% { background-color: transparent; }
}

[data-state="dirty"] {
  border-left: 3px solid var(--wa-color-warning-fill-loud);
}

[data-state="saving"] {
  border-left: 3px solid var(--wa-color-info-fill-loud);
  opacity: 0.8;
}

[data-state="saved"] {
  border-left: 3px solid var(--wa-color-success-fill-loud);
  animation: highlight 2s ease-in-out;
}

[data-state="error"] {
  border-left: 3px solid var(--wa-color-danger-fill-loud);
}

.field-container {
  margin-bottom: var(--wa-space-m);
  padding: var(--wa-space-xs);
  transition: all 0.3s ease;
}

/* Animate elements that are being modified */
[data-modified="true"] {
  background-color: rgba(var(--wa-color-warning-fill-quiet-rgb), 0.2);
}

/* Resource items in reactive view */
.resource-item {
  margin-bottom: var(--wa-space-m);
  padding: var(--wa-space-m);
  border-radius: var(--wa-border-radius-m);
  box-shadow: var(--wa-shadow-s);
  background-color: var(--wa-color-surface-raised);
}

.resource-fields {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: var(--wa-space-m);
  margin-top: var(--wa-space-m);
}
```

### 6. Deployment

Deploy to a static hosting service:

1. **Build the application** (optional, since we're using vanilla JS):
   - No build step is required if you're using ES modules directly
   - For production, you might want to minify the files using a tool like `terser`

2. **Choose a hosting service**:
   - Netlify
   - Vercel
   - GitHub Pages
   - AWS S3 + CloudFront
   - Firebase Hosting

3. **Configure for SPA routing** (if using client-side routing):

For Netlify, create a `_redirects` file:
```
/*    /index.html   200
```

For Vercel, create a `vercel.json` file:
```json
{
  "rewrites": [{ "source": "/(.*)", "destination": "/index.html" }]
}
```

4. **Configure your API**:
   - Ensure CORS is properly configured on your API
   - Set up proper authentication for API requests
   - Implement schema discovery endpoints on the backend

### 7. Testing The Observer Pattern

To test that the MutationObserver integration is working correctly:

1. **Monitor DOM changes in dev tools**:
   ```javascript
   // Run in browser console
   const observer = new MutationObserver((mutations) => {
     console.log('Mutations detected:', mutations);
   });
   
   observer.observe(document.body, { 
     childList: true, 
     subtree: true, 
     attributes: true 
   });
   ```

2. **Create a test field updater**:
   ```javascript
   // Run in browser console to simulate updates
   function simulateChange(resourceName, id, field, value) {
     const selector = `[data-resource="${resourceName}"] [data-id="${id}"][data-field="${field}"]`;
     const element = document.querySelector(selector);
     
     if (element) {
       // Update value
       if (element.tagName === 'WA-INPUT') {
         element.value = value;
       } else {
         element.textContent = value;
       }
       
       // Update attributes to trigger observer
       element.setAttribute('data-value', value);
       element.setAttribute('data-modified', 'true');
       element.setAttribute('data-state', 'dirty');
       
       console.log('Element updated:', element);
     } else {
       console.warn('Element not found:', selector);
     }
   }
   
   // Example usage
   simulateChange('users', '123', 'name', 'John Updated');
   ```

3. **Test the full synchronization flow**:
   - Open the application in two browser windows
   - Make changes in one window and observe them synchronizing to the other
   - Check the WebSocket traffic in the Network tab of dev tools

## Resources

- [JSON Schema](https://json-schema.org/) - Format for describing JSON data
- [OpenAPI Specification](https://swagger.io/specification/) - Another approach to API description
- [Web Components MDN Guide](https://developer.mozilla.org/en-US/docs/Web/API/Web_components)
- [Lit Documentation](https://lit.dev/)
- [WebAwesome Documentation](https://backers.webawesome.com/docs/)
- [MutationObserver API](https://developer.mozilla.org/en-US/docs/Web/API/MutationObserver) - Core browser API for observing DOM changes
- [WebAwesome 3.0 GitHub](https://github.com/shoelace-style/webawesome-alpha) - Repository for WebAwesome 3.0

## Conclusion

By implementing this schema-driven UI system with WebAwesome 3.0 and MutationObserver integration, you create a powerful, self-adapting interface that automatically responds to changes in your REST API and provides real-time updates.

Key benefits of this approach include:

1. **Automatic UI Generation**: Components adapt based on schema metadata, eliminating the need to create custom UIs for every resource
2. **Real-time Reactivity**: The MutationObserver pattern enables automatic UI updates in response to data changes
3. **Bidirectional Synchronization**: Changes propagate from UI to server and from server to UI in real-time
4. **Visual Feedback**: Users receive immediate feedback on the status of their changes
5. **Extensibility**: The extension system allows customizing behavior for specific resources
6. **Standards-Based**: Built on web standards (Web Components, MutationObserver) for future compatibility
7. **No Build Step**: Vanilla JavaScript approach simplifies development and deployment
8. **Scalability**: Works well with microservice architectures and growing data models

This approach is particularly valuable for admin interfaces, internal tools, and data-heavy applications where UI requirements evolve frequently and changes need to be reflected in real-time across multiple clients.

By leveraging WebAwesome 3.0's integration with MutationObserver, you create a UI that is not just data-driven but truly reactive, providing a seamless and responsive user experience.
