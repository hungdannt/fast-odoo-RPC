/* Custom JavaScript for Zenoo RPC documentation */

document.addEventListener('DOMContentLoaded', function() {
    // Add copy buttons to code blocks
    addCopyButtons();
    
    // Add version badges
    addVersionBadges();
    
    // Initialize feature cards
    initializeFeatureCards();
    
    // Add smooth scrolling
    addSmoothScrolling();
    
    // Initialize search enhancements
    initializeSearchEnhancements();
});

/**
 * Add copy buttons to code blocks
 */
function addCopyButtons() {
    const codeBlocks = document.querySelectorAll('pre code');
    
    codeBlocks.forEach(function(codeBlock) {
        const pre = codeBlock.parentElement;
        
        // Skip if already has copy button
        if (pre.querySelector('.copy-button')) {
            return;
        }
        
        // Create copy button
        const copyButton = document.createElement('button');
        copyButton.className = 'copy-button';
        copyButton.innerHTML = '📋';
        copyButton.title = 'Copy to clipboard';
        
        // Style the button
        copyButton.style.cssText = `
            position: absolute;
            top: 8px;
            right: 8px;
            background: rgba(0, 0, 0, 0.7);
            color: white;
            border: none;
            border-radius: 4px;
            padding: 4px 8px;
            cursor: pointer;
            font-size: 12px;
            opacity: 0;
            transition: opacity 0.2s ease;
        `;
        
        // Make pre relative for absolute positioning
        pre.style.position = 'relative';
        
        // Show button on hover
        pre.addEventListener('mouseenter', function() {
            copyButton.style.opacity = '1';
        });
        
        pre.addEventListener('mouseleave', function() {
            copyButton.style.opacity = '0';
        });
        
        // Copy functionality
        copyButton.addEventListener('click', function() {
            const text = codeBlock.textContent;
            
            if (navigator.clipboard) {
                navigator.clipboard.writeText(text).then(function() {
                    showCopyFeedback(copyButton, 'Copied!');
                }).catch(function() {
                    fallbackCopy(text, copyButton);
                });
            } else {
                fallbackCopy(text, copyButton);
            }
        });
        
        pre.appendChild(copyButton);
    });
}

/**
 * Fallback copy method for older browsers
 */
function fallbackCopy(text, button) {
    const textArea = document.createElement('textarea');
    textArea.value = text;
    textArea.style.position = 'fixed';
    textArea.style.left = '-999999px';
    textArea.style.top = '-999999px';
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();
    
    try {
        document.execCommand('copy');
        showCopyFeedback(button, 'Copied!');
    } catch (err) {
        showCopyFeedback(button, 'Failed');
    }
    
    document.body.removeChild(textArea);
}

/**
 * Show copy feedback
 */
function showCopyFeedback(button, message) {
    const originalText = button.innerHTML;
    button.innerHTML = message;
    button.style.background = message === 'Copied!' ? '#4caf50' : '#f44336';
    
    setTimeout(function() {
        button.innerHTML = originalText;
        button.style.background = 'rgba(0, 0, 0, 0.7)';
    }, 1500);
}

/**
 * Add version badges to API elements
 */
function addVersionBadges() {
    // Add "New in 0.3.0" badges to relevant sections
    const newFeatures = [
        'Batch Operations',
        'Transaction Management',
        'Retry Mechanisms',
        'Intelligent Caching'
    ];
    
    newFeatures.forEach(function(feature) {
        const headings = document.querySelectorAll('h1, h2, h3, h4, h5, h6');
        headings.forEach(function(heading) {
            if (heading.textContent.includes(feature)) {
                const badge = document.createElement('span');
                badge.className = 'version-badge';
                badge.textContent = 'New in 0.3.0';
                heading.appendChild(badge);
            }
        });
    });
}

/**
 * Initialize feature cards with hover effects
 */
function initializeFeatureCards() {
    const featureCards = document.querySelectorAll('.zenoo-feature-card');
    
    featureCards.forEach(function(card) {
        card.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-4px)';
            this.style.boxShadow = '0 8px 24px rgba(0, 0, 0, 0.15)';
        });
        
        card.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0)';
            this.style.boxShadow = '0 2px 4px rgba(0, 0, 0, 0.05)';
        });
    });
}

/**
 * Add smooth scrolling to anchor links
 */
function addSmoothScrolling() {
    const anchorLinks = document.querySelectorAll('a[href^="#"]');
    
    anchorLinks.forEach(function(link) {
        link.addEventListener('click', function(e) {
            const targetId = this.getAttribute('href').substring(1);
            const targetElement = document.getElementById(targetId);
            
            if (targetElement) {
                e.preventDefault();
                targetElement.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
                
                // Update URL without jumping
                history.pushState(null, null, '#' + targetId);
            }
        });
    });
}

/**
 * Initialize search enhancements
 */
function initializeSearchEnhancements() {
    const searchInput = document.querySelector('.md-search__input');
    
    if (searchInput) {
        // Add search suggestions
        searchInput.addEventListener('input', function() {
            const query = this.value.toLowerCase();
            
            if (query.length > 2) {
                highlightSearchTerms(query);
            }
        });
        
        // Add keyboard shortcuts
        document.addEventListener('keydown', function(e) {
            // Ctrl/Cmd + K to focus search
            if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
                e.preventDefault();
                searchInput.focus();
            }
            
            // Escape to clear search
            if (e.key === 'Escape' && document.activeElement === searchInput) {
                searchInput.value = '';
                searchInput.blur();
            }
        });
    }
}

/**
 * Highlight search terms in content
 */
function highlightSearchTerms(query) {
    // Remove existing highlights
    const existingHighlights = document.querySelectorAll('.search-highlight');
    existingHighlights.forEach(function(highlight) {
        const parent = highlight.parentNode;
        parent.replaceChild(document.createTextNode(highlight.textContent), highlight);
        parent.normalize();
    });
    
    // Add new highlights
    if (query.length > 2) {
        const walker = document.createTreeWalker(
            document.querySelector('.md-content'),
            NodeFilter.SHOW_TEXT,
            null,
            false
        );
        
        const textNodes = [];
        let node;
        
        while (node = walker.nextNode()) {
            textNodes.push(node);
        }
        
        textNodes.forEach(function(textNode) {
            const text = textNode.textContent;
            const regex = new RegExp(`(${query})`, 'gi');
            
            if (regex.test(text)) {
                const highlightedHTML = text.replace(regex, '<mark class="search-highlight">$1</mark>');
                const wrapper = document.createElement('span');
                wrapper.innerHTML = highlightedHTML;
                textNode.parentNode.replaceChild(wrapper, textNode);
            }
        });
    }
}

/**
 * Add table of contents enhancements
 */
function enhanceTableOfContents() {
    const tocLinks = document.querySelectorAll('.md-nav__link');
    
    tocLinks.forEach(function(link) {
        link.addEventListener('click', function() {
            // Remove active class from all links
            tocLinks.forEach(function(l) {
                l.classList.remove('md-nav__link--active');
            });
            
            // Add active class to clicked link
            this.classList.add('md-nav__link--active');
        });
    });
}

/**
 * Add progress indicator for long pages
 */
function addProgressIndicator() {
    const progressBar = document.createElement('div');
    progressBar.className = 'reading-progress';
    progressBar.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 0%;
        height: 3px;
        background: var(--zenoo-primary);
        z-index: 1000;
        transition: width 0.1s ease;
    `;
    
    document.body.appendChild(progressBar);
    
    window.addEventListener('scroll', function() {
        const scrollTop = window.pageYOffset;
        const docHeight = document.body.scrollHeight - window.innerHeight;
        const scrollPercent = (scrollTop / docHeight) * 100;
        
        progressBar.style.width = scrollPercent + '%';
    });
}

/**
 * Initialize all enhancements
 */
function initializeEnhancements() {
    enhanceTableOfContents();
    addProgressIndicator();
}

// Initialize enhancements when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeEnhancements);
} else {
    initializeEnhancements();
}

// Add analytics tracking for documentation usage
function trackDocumentationUsage() {
    // Track page views
    if (typeof gtag !== 'undefined') {
        gtag('config', 'GA_MEASUREMENT_ID', {
            page_title: document.title,
            page_location: window.location.href
        });
    }
    
    // Track code copy events
    document.addEventListener('click', function(e) {
        if (e.target.classList.contains('copy-button')) {
            if (typeof gtag !== 'undefined') {
                gtag('event', 'code_copy', {
                    event_category: 'documentation',
                    event_label: 'code_block_copied'
                });
            }
        }
    });
    
    // Track search usage
    const searchInput = document.querySelector('.md-search__input');
    if (searchInput) {
        searchInput.addEventListener('input', debounce(function() {
            if (this.value.length > 2 && typeof gtag !== 'undefined') {
                gtag('event', 'search', {
                    event_category: 'documentation',
                    event_label: 'search_query',
                    value: this.value.length
                });
            }
        }, 1000));
    }
}

/**
 * Debounce function to limit event firing
 */
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Initialize analytics tracking
trackDocumentationUsage();
