import React from 'react';
import './Footer.css';

/**
 * Footer Component
 * Site footer with links and info
 */
const Footer = () => {
  const footerSections = [
    {
      title: 'Product',
      links: [
        { label: 'Dashboard', href: '#' },
        { label: 'Predictions', href: '#' },
        { label: 'Analytics', href: '#' },
        { label: 'API', href: '#' },
      ],
    },
    {
      title: 'Resources',
      links: [
        { label: 'Documentation', href: '#' },
        { label: 'Tutorials', href: '#' },
        { label: 'Blog', href: '#' },
        { label: 'FAQ', href: '#' },
      ],
    },
    {
      title: 'Company',
      links: [
        { label: 'About', href: '#' },
        { label: 'Contact', href: '#' },
        { label: 'Privacy', href: '#' },
        { label: 'Terms', href: '#' },
      ],
    },
  ];
  
  const socialLinks = [
    { icon: '𝕏', label: 'Twitter', href: '#' },
    { icon: '📷', label: 'Instagram', href: '#' },
    { icon: '▶️', label: 'YouTube', href: '#' },
    { icon: '💼', label: 'LinkedIn', href: '#' },
  ];
  
  return (
    <footer className="footer">
      <div className="footer-container">
        {/* Top Section */}
        <div className="footer-top">
          {/* Brand */}
          <div className="footer-brand">
            <div className="footer-logo">
              <span className="footer-logo-icon">⚔️</span>
              <span className="footer-logo-text">SCIPHR</span>
            </div>
            <p className="footer-tagline">
              AI-powered UFC fight predictions. Making data-driven betting decisions easier.
            </p>
            <div className="footer-social">
              {socialLinks.map((social) => (
                <a 
                  key={social.label}
                  href={social.href}
                  className="social-link"
                  aria-label={social.label}
                  title={social.label}
                >
                  {social.icon}
                </a>
              ))}
            </div>
          </div>
          
          {/* Links Sections */}
          {footerSections.map((section) => (
            <div key={section.title} className="footer-section">
              <h4 className="footer-section-title">{section.title}</h4>
              <ul className="footer-links">
                {section.links.map((link) => (
                  <li key={link.label}>
                    <a href={link.href} className="footer-link">
                      {link.label}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
        
        {/* Divider */}
        <div className="footer-divider"></div>
        
        {/* Bottom Section */}
        <div className="footer-bottom">
          <p className="footer-copyright">
            © {new Date().getFullYear()} SCIPHR. All rights reserved.
          </p>
          <div className="footer-stats">
            <div className="stat">
              <span className="stat-value">1,247</span>
              <span className="stat-label">Predictions Made</span>
            </div>
            <div className="stat">
              <span className="stat-value">85.2%</span>
              <span className="stat-label">Accuracy Rate</span>
            </div>
            <div className="stat">
              <span className="stat-value">24/7</span>
              <span className="stat-label">Live Updates</span>
            </div>
          </div>
        </div>
      </div>
    </footer>
  );
};

export default Footer;