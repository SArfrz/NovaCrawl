/**
 * E-E-A-T Analyzer Plugin for SArfrzCrawl
 * Analyzes Experience, Expertise, Authoritativeness, Trust signals on crawled pages
 *
 * @author SArfrzCrawl Community
 * @version 1.0.0
 */

NovaCrawlPlugin.register({
    // Plugin metadata
    id: 'e-e-a-t',
    name: 'E-E-A-T Analyzer',
    version: '1.0.0',
    author: 'SArfrzCrawl Community',
    description: 'Analyzes Experience, Expertise, Authoritativeness, Trust (E-E-A-T) signals on your website',

    // Tab configuration
    tab: {
        label: 'E-E-A-T',
        icon: '🎓',
        position: 'end' // Appears after all built-in tabs
    },

    // Plugin initialization
    onLoad() {
        console.log('📊 E-E-A-T Analyzer loaded');
    },

    // Called when tab becomes active
    onTabActivate(container, data) {
        console.log('🎓 E-E-A-T tab activated with', data.urls.length, 'URLs');
        this.render(container, data);
    },

    // Called during live crawls when data updates
    onDataUpdate(data) {
        if (this.isActive && this.container) {
            this.render(this.container, data);
        }
    },

    // Called when crawl completes
    onCrawlComplete(data) {
        console.log('✅ E-E-A-T analysis complete for', data.urls.length, 'URLs');
        if (this.isActive && this.container) {
            this.render(this.container, data);
        }
    },

    // Main render function
    render(container, data) {
        const { urls, links } = data;

        if (!urls || urls.length === 0) {
            container.innerHTML = this.renderEmptyState();
            return;
        }

        // Analyze E-E-A-T signals
        const analysis = this.analyzeEEAT(urls, links);

        // Render the analysis
        container.innerHTML = `
            <div class="plugin-content" style="padding: 20px; overflow-y: auto; max-height: calc(100vh - 280px);">
                ${this.renderHeader(analysis)}
                ${this.renderScoreCards(analysis)}
                ${this.renderSignalsBreakdown(analysis)}
                ${this.renderTopPages(analysis)}
                ${this.renderRecommendations(analysis)}
            </div>
        `;
    },

    // Render header section
    renderHeader(analysis) {
        return `
            <div class="plugin-header" style="margin-bottom: 32px;">
                <h2 style="font-size: 28px; font-weight: 700; margin-bottom: 8px; color: #e5e7eb;">
                    🎓 E-E-A-T Analysis
                </h2>
                <p style="color: #9ca3af; font-size: 14px;">
                    Experience, Expertise, Authoritativeness, and Trust signals across your website
                </p>
            </div>
        `;
    },

    // Render score cards
    renderScoreCards(analysis) {
        const scoreClass = this.getScoreClass(analysis.overallScore);
        const scoreColor = this.getScoreColor(analysis.overallScore);

        return `
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 20px; margin-bottom: 32px;">
                <div class="stat-card" style="background: #1f2937; padding: 24px; border-radius: 12px; border: 1px solid #374151;">
                    <div style="font-size: 14px; color: #9ca3af; margin-bottom: 12px; text-transform: uppercase; letter-spacing: 1px;">
                        Overall E-E-A-T Score
                    </div>
                    <div style="font-size: 48px; font-weight: 700; color: ${scoreColor}; margin-bottom: 8px;">
                        ${analysis.overallScore}
                    </div>
                    <div style="font-size: 13px; color: #6b7280;">
                        Out of 100
                    </div>
                </div>

                <div class="stat-card" style="background: #1f2937; padding: 24px; border-radius: 12px; border: 1px solid #374151;">
                    <div style="font-size: 14px; color: #9ca3af; margin-bottom: 12px; text-transform: uppercase; letter-spacing: 1px;">
                        Content Pages with Author
                    </div>
                    <div style="font-size: 48px; font-weight: 700; color: #10b981; margin-bottom: 8px;">
                        ${analysis.contentPagesWithAuthor}
                    </div>
                    <div style="font-size: 13px; color: #6b7280;">
                        ${this.getPercentage(analysis.contentPagesWithAuthor, analysis.contentPages)}% of ${analysis.contentPages} content pages
                    </div>
                </div>

                <div class="stat-card" style="background: #1f2937; padding: 24px; border-radius: 12px; border: 1px solid #374151;">
                    <div style="font-size: 14px; color: #9ca3af; margin-bottom: 12px; text-transform: uppercase; letter-spacing: 1px;">
                        Content Pages with Schema
                    </div>
                    <div style="font-size: 48px; font-weight: 700; color: #3b82f6; margin-bottom: 8px;">
                        ${analysis.contentPagesWithSchema}
                    </div>
                    <div style="font-size: 13px; color: #6b7280;">
                        ${this.getPercentage(analysis.contentPagesWithSchema, analysis.contentPages)}% of ${analysis.contentPages} content pages
                    </div>
                </div>

                <div class="stat-card" style="background: #1f2937; padding: 24px; border-radius: 12px; border: 1px solid #374151;">
                    <div style="font-size: 14px; color: #9ca3af; margin-bottom: 12px; text-transform: uppercase; letter-spacing: 1px;">
                        External Citations
                    </div>
                    <div style="font-size: 48px; font-weight: 700; color: #f59e0b; margin-bottom: 8px;">
                        ${analysis.externalCitations}
                    </div>
                    <div style="font-size: 13px; color: #6b7280;">
                        Average ${analysis.avgExternalLinks.toFixed(1)} per content page
                    </div>
                </div>
            </div>
        `;
    },

    // Render signals breakdown
    renderSignalsBreakdown(analysis) {
        return `
            <div style="background: #1f2937; padding: 24px; border-radius: 12px; border: 1px solid #374151; margin-bottom: 32px;">
                <h3 style="font-size: 18px; font-weight: 600; margin-bottom: 20px; color: #e5e7eb;">
                    Trust Signals Breakdown
                </h3>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px;">
                    ${this.renderSignalItem('✍️', 'Author Attribution', analysis.contentPagesWithAuthor, analysis.contentPages, 'content pages')}
                    ${this.renderSignalItem('📊', 'Structured Data', analysis.contentPagesWithSchema, analysis.contentPages, 'content pages')}
                    ${this.renderSignalItem('🔗', 'External Citations', analysis.contentPagesWithExtLinks, analysis.contentPages, 'content pages')}
                    ${this.renderSignalItem('🏷️', 'Open Graph Tags', analysis.pagesWithOGTags, analysis.shareablePages, 'shareable pages')}
                    ${this.renderSignalItem('🔒', 'HTTPS Secure', analysis.securePages, analysis.totalPages, 'pages')}
                    ${this.renderSignalItem('📝', 'Sufficient Content', analysis.pagesWithGoodContent, analysis.contentPages, 'content pages')}
                </div>
            </div>
        `;
    },

    // Render individual signal item
    renderSignalItem(icon, label, count, total, denomLabel = 'pages') {
        const percentage = this.getPercentage(count, total);
        const barColor = percentage >= 75 ? '#10b981' : percentage >= 50 ? '#f59e0b' : '#ef4444';
        const naLabel = total === 0 ? 'N/A' : `${count}/${total}`;

        return `
            <div style="background: #0f172a; padding: 16px; border-radius: 8px; border: 1px solid #1e293b;">
                <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 12px;">
                    <span style="font-size: 20px;">${icon}</span>
                    <div style="font-size: 13px; color: #cbd5e1; font-weight: 500;">${label}</div>
                </div>
                <div style="font-size: 24px; font-weight: 700; color: #e5e7eb; margin-bottom: 8px;">
                    ${naLabel}
                </div>
                <div style="background: #1e293b; height: 6px; border-radius: 3px; overflow: hidden; margin-bottom: 6px;">
                    <div style="background: ${barColor}; height: 100%; width: ${total === 0 ? 0 : percentage}%; transition: width 0.3s;"></div>
                </div>
                <div style="font-size: 12px; color: #6b7280;">
                    ${total === 0 ? 'No ' + denomLabel + ' detected' : percentage + '% of ' + denomLabel}
                </div>
            </div>
        `;
    },

    // Render top pages by E-E-A-T score
    renderTopPages(analysis) {
        return `
            <div style="background: #ffffff; padding: 24px; border-radius: 12px; border: 1px solid #e2e8f0; margin-bottom: 32px;">
                <h3 style="font-size: 18px; font-weight: 600; margin-bottom: 20px; color: #1e293b;">
                    Top Pages by E-E-A-T Score
                </h3>
                <div style="overflow-x: auto;">
                    <table class="data-table" style="width: 100%; border-collapse: collapse;">
                        <thead>
                            <tr style="border-bottom: 2px solid #e2e8f0; background: #f8fafc;">
                                <th style="padding: 12px; text-align: left; color: #475569; font-size: 13px; font-weight: 600;">URL</th>
                                <th style="padding: 12px; text-align: center; color: #475569; font-size: 13px; font-weight: 600;">Score</th>
                                <th style="padding: 12px; text-align: center; color: #475569; font-size: 13px; font-weight: 600;">Author</th>
                                <th style="padding: 12px; text-align: center; color: #475569; font-size: 13px; font-weight: 600;">Schema</th>
                                <th style="padding: 12px; text-align: center; color: #475569; font-size: 13px; font-weight: 600;">Ext. Links</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${analysis.topPages.slice(0, 10).map((page, i) => this.renderPageRow(page, i)).join('')}
                        </tbody>
                    </table>
                </div>
            </div>
        `;
    },

    // Render individual page row
    renderPageRow(page, index) {
        const scoreColor = this.getScoreColor(page.score);
        const rowBg = index % 2 === 0 ? '#ffffff' : '#f8fafc';
        const authorCell = page.isContent
            ? (page.hasAuthor ? '✅' : '❌')
            : '<span style="color:#94a3b8;font-size:11px;">N/A</span>';
        return `
            <tr style="border-bottom: 1px solid #e2e8f0; background: ${rowBg};"
                onmouseover="this.style.background='#e0f2fe'" onmouseout="this.style.background='${rowBg}'">
                <td style="padding: 12px; color: #334155; font-size: 13px; max-width: 400px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                    ${this.utils.escapeHtml(page.url)}
                </td>
                <td style="padding: 12px; text-align: center; font-weight: 600; font-size: 14px; color: ${scoreColor};">
                    ${page.score}
                </td>
                <td style="padding: 12px; text-align: center; font-size: 20px;">
                    ${authorCell}
                </td>
                <td style="padding: 12px; text-align: center; font-size: 20px;">
                    ${page.hasSchema ? '✅' : '❌'}
                </td>
                <td style="padding: 12px; text-align: center; color: #334155; font-size: 13px;">
                    ${page.externalLinks}
                </td>
            </tr>
        `;
    },

    // Render recommendations
    renderRecommendations(analysis) {
        const recommendations = this.generateRecommendations(analysis);

        return `
            <div style="background: #1f2937; padding: 24px; border-radius: 12px; border: 1px solid #374151;">
                <h3 style="font-size: 18px; font-weight: 600; margin-bottom: 20px; color: #e5e7eb;">
                    💡 Recommendations to Improve E-E-A-T
                </h3>
                <div style="display: flex; flex-direction: column; gap: 12px;">
                    ${recommendations.map(rec => this.renderRecommendation(rec)).join('')}
                </div>
            </div>
        `;
    },

    // Render individual recommendation
    renderRecommendation(rec) {
        const priorityColors = {
            high: '#ef4444',
            medium: '#f59e0b',
            low: '#3b82f6'
        };

        return `
            <div style="background: #0f172a; padding: 16px; border-radius: 8px; border-left: 4px solid ${priorityColors[rec.priority]};">
                <div style="display: flex; align-items: start; gap: 12px;">
                    <span style="font-size: 24px;">${rec.icon}</span>
                    <div style="flex: 1;">
                        <div style="font-weight: 600; color: #e5e7eb; margin-bottom: 4px; font-size: 14px;">
                            ${rec.title}
                        </div>
                        <div style="color: #9ca3af; font-size: 13px; line-height: 1.6;">
                            ${rec.description}
                        </div>
                    </div>
                    <div style="background: ${priorityColors[rec.priority]}20; color: ${priorityColors[rec.priority]}; padding: 4px 12px; border-radius: 12px; font-size: 11px; font-weight: 600; text-transform: uppercase;">
                        ${rec.priority}
                    </div>
                </div>
            </div>
        `;
    },

    // Empty state
    renderEmptyState() {
        return `
            <div style="padding: 20px; overflow-y: auto; max-height: calc(100vh - 280px);">
                <div class="empty-state" style="text-align: center; padding: 60px 20px;">
                    <div style="font-size: 64px; margin-bottom: 20px;">🎓</div>
                    <h3 style="font-size: 24px; font-weight: 600; color: #e5e7eb; margin-bottom: 12px;">
                        No Data Yet
                    </h3>
                    <p style="color: #9ca3af; font-size: 14px;">
                        Start crawling to analyze E-E-A-T signals on your website
                    </p>
                </div>
            </div>
        `;
    },

    // Extract all JSON-LD @type values as lowercase array
    getLdTypes(jsonLd) {
        const types = new Set();
        for (const node of (jsonLd || [])) {
            if (!node || typeof node !== 'object') continue;
            const raw = node['@type'] || '';
            (Array.isArray(raw) ? raw : [raw]).forEach(t => types.add(String(t).toLowerCase()));
        }
        return types;
    },

    // Full multi-signal page type classifier — mirrors Python classify_page()
    classifyPage(urlData) {
        const u = (urlData.url || '').toLowerCase();
        const wordCount = urlData.word_count || 0;
        const jsonLd = urlData.json_ld || [];
        const ogTags = urlData.og_tags || {};
        const ldTypes = this.getLdTypes(jsonLd);

        const scores = { article: 0, product: 0, collection: 0, organization: 0, event: 0, faq: 0, profile: 0, structural: 0 };
        const add = (type, pts) => { scores[type] += pts; };

        // STRUCTURAL
        if (/^https?:\/\/[^/]+(\/)?(\?.*)?$/.test(u)) add('structural', 5);
        if (/\/(login|logout|register|signup|sign-in|checkout|cart|basket|404|403|500|sitemap)(s)?(\/|$|\?)/.test(u)) add('structural', 5);
        if (/\/(search|results)(\/|$|\?)/.test(u) || u.includes('?s=') || u.includes('?q=')) add('structural', 5);
        if (/\/feed(\/|$|\?)/.test(u)) add('structural', 5);
        if (/\/(tag|tags|category|categories)(\/|$|\?)/.test(u)) add('structural', 5);

        // ARTICLE
        const articleLd = new Set(['article','blogposting','newsarticle','techarticle','report','scholarlyarticle']);
        if ([...ldTypes].some(t => articleLd.has(t))) add('article', 5);
        // og:type=article is +2 only — WordPress/Yoast sets it on ALL pages by default
        if ((ogTags.type || '').toLowerCase() === 'article') add('article', 2);
        // article:published_time is strong — CMS only adds to real articles
        if (ogTags.published_time || ogTags['article:published_time']) add('article', 4);
        if (ogTags.author || ogTags['article:author']) add('article', 3);
        if (/\/(blog|article|post|news|guide|tutorial|review|story|insight|learn|knowledge)(s)?(\/|$|\?)/i.test(u)) add('article', 4);
        if (/\/\d{4}\/\d{2}\//.test(u)) add('article', 3);
        if (wordCount >= 600) add('article', 3);
        else if (wordCount >= 300) add('article', 2);

        // PRODUCT
        if (ldTypes.has('product')) add('product', 5);
        if (['product','og:product'].includes((ogTags.type || '').toLowerCase())) add('product', 4);
        if (ogTags['price:amount'] || ogTags.price) add('product', 4);
        if (/\/(product|item|buy|pd)(s)?(\/|$|\?|\/)/.test(u)) add('product', 4);
        if (/\/(shop|store)(\/[^/]+){1,2}$/.test(u)) add('product', 3);

        // COLLECTION
        if ([...ldTypes].some(t => ['collectionpage','itemlist','productcollection'].includes(t))) add('collection', 5);
        if (/\/(category|collection|catalog|listing|department|tag|archive)(s)?(\/|$|\?)/.test(u)) add('collection', 4);
        if (/\/(shop|store)(\/|$|\?)$/.test(u)) add('collection', 3);
        if (/\/page\/\d+/.test(u) || /[?&](page|p)=\d+/.test(u)) add('collection', 3);

        // ORGANIZATION
        if ([...ldTypes].some(t => ['organization','localbusiness','corporation','nonprofit','restaurant'].includes(t))) add('organization', 5);
        if (/\/(about|about-us|our-story|contact|contact-us|privacy|terms|services|pricing)(\/|$|\?)/.test(u)) add('organization', 4);

        // EVENT
        if (ldTypes.has('event')) add('event', 5);
        if ((ogTags.type || '').toLowerCase() === 'event') add('event', 4);
        if (/\/(event|events|webinar|conference|meetup|workshop)(\/|$|\?)/.test(u)) add('event', 4);

        // FAQ
        if (ldTypes.has('faqpage')) add('faq', 5);
        if (/\/(faq|faqs|help|frequently-asked|questions)(\/|$|\?)/.test(u)) add('faq', 4);

        // PROFILE
        if (ldTypes.has('person') || ldTypes.has('profilepage')) add('profile', 5);
        if (/\/(author|team|staff|member|people|person|bio|profile)(s)?(\/[^/]+)?(\/|$|\?)/.test(u)) add('profile', 4);

        // DETERMINE WINNER
        let pageType = 'unknown';
        if (scores.structural >= 5) {
            pageType = 'structural';
        } else {
            const { structural: _s, ...rest } = scores;
            const best = Object.entries(rest).sort((a, b) => b[1] - a[1])[0];
            if (best[1] >= 5) pageType = best[0];
        }

        const typeConfig = {
            article:      { needsAuthor: true,  needsSchema: true,  expectedSchema: 'Article / BlogPosting' },
            product:      { needsAuthor: false, needsSchema: true,  expectedSchema: 'Product' },
            collection:   { needsAuthor: false, needsSchema: false, expectedSchema: 'CollectionPage / ItemList' },
            organization: { needsAuthor: false, needsSchema: false, expectedSchema: 'Organization / LocalBusiness' },
            event:        { needsAuthor: false, needsSchema: true,  expectedSchema: 'Event' },
            faq:          { needsAuthor: false, needsSchema: true,  expectedSchema: 'FAQPage' },
            profile:      { needsAuthor: false, needsSchema: false, expectedSchema: 'Person' },
            structural:   { needsAuthor: false, needsSchema: false, expectedSchema: null },
            unknown:      { needsAuthor: false, needsSchema: false, expectedSchema: null },
        };
        const cfg = typeConfig[pageType];

        return {
            pageType,
            scores,
            needsAuthor: cfg.needsAuthor,
            needsSchema: cfg.needsSchema,
            expectedSchema: cfg.expectedSchema,
            isContent: pageType === 'article',
            isStructural: pageType === 'structural',
            score: scores[pageType] || 0,
        };
    },

    // Convenience wrapper for backward compat
    isContentPage(urlData) {
        return this.classifyPage(urlData).isContent;
    },

    // Returns true if this page should have OG tags (shareable pages)
    isShareablePage(url) {
        const u = (url.url || '').toLowerCase();
        // Exclude pages that are never shared socially
        const nonShareable = /\/(login|logout|register|signup|checkout|cart|search|admin|api|feed|sitemap|404|403|500)(\/|$|\?|\.)/;
        return !nonShareable.test(u);
    },

    // Analyze E-E-A-T signals across all URLs
    analyzeEEAT(urls, links) {
        let totalScore = 0;
        let pagesWithAuthor = 0;
        let contentPages = 0;
        let contentPagesWithAuthor = 0;
        let pagesWithSchema = 0;
        let contentPagesWithSchema = 0;
        let pagesWithExternalLinks = 0;
        let contentPagesWithExtLinks = 0;
        let pagesWithOGTags = 0;
        let shareablePages = 0;
        let securePages = 0;
        let pagesWithGoodContent = 0;
        let externalCitations = 0;
        const pageScores = [];

        urls.forEach(url => {
            let score = 0;
            const urlData = {
                url: url.url,
                score: 0,
                hasAuthor: false,
                hasSchema: false,
                isContent: false,
                externalLinks: url.external_links || 0
            };

            // Check for HTTPS (10 points)
            if (url.url && url.url.startsWith('https://')) {
                score += 10;
                securePages++;
            }

            // Classify page type using multi-signal classifier
            const pageClass = this.classifyPage(url);
            const isContent = pageClass.isContent;
            const isStructural = pageClass.isStructural;
            const needsAuthor = pageClass.needsAuthor;
            const needsSchema = pageClass.needsSchema;
            urlData.isContent = isContent;
            urlData.pageType = pageClass.pageType;
            if (isContent) contentPages++;

            // Author check (20 points) — only article pages need authors
            const hasAuthor = !!(url.meta_author || url.author || (url.og_tags && (url.og_tags.author || url.og_tags['article:author'])));
            if (hasAuthor) {
                score += 20;
                pagesWithAuthor++;
                urlData.hasAuthor = true;
                if (isContent) contentPagesWithAuthor++;
            } else if (!needsAuthor) {
                score += 20; // not expected — full points
            }

            // Schema check (25 points) — weighted by whether schema is expected
            if (url.json_ld && url.json_ld.length > 0) {
                score += 25;
                pagesWithSchema++;
                urlData.hasSchema = true;
                if (isContent) contentPagesWithSchema++;
            } else if (!needsSchema) {
                score += 25; // schema not expected for this page type — full points
            }

            // External citations (15 points) — only article pages
            const extLinks = url.external_links || 0;
            if (isContent) {
                if (extLinks > 0) {
                    score += Math.min(15, extLinks * 3);
                    pagesWithExternalLinks++;
                    contentPagesWithExtLinks++;
                    externalCitations += extLinks;
                }
            } else {
                score += 15;
                externalCitations += extLinks;
                if (extLinks > 0) pagesWithExternalLinks++;
            }

            // OG tags (10 points) — not expected on structural/utility pages
            const isShareable = this.isShareablePage(url);
            if (isShareable) shareablePages++;
            if (url.og_tags && url.og_tags.title) {
                score += 10;
                pagesWithOGTags++;
            } else if (!isShareable || isStructural) {
                score += 10;
            }

            // Content depth (20 points) — only article pages
            const wordCount = url.word_count || 0;
            if (isContent) {
                if (wordCount >= 300) { score += 20; pagesWithGoodContent++; }
                else if (wordCount >= 150) score += 10;
            } else {
                score += 20;
            }

            urlData.score = Math.min(100, score);
            totalScore += urlData.score;
            pageScores.push(urlData);
        });

        // Sort pages by score
        pageScores.sort((a, b) => b.score - a.score);

        return {
            totalPages: urls.length,
            overallScore: urls.length > 0 ? Math.round(totalScore / urls.length) : 0,
            pagesWithAuthor,
            contentPages,
            contentPagesWithAuthor,
            pagesWithSchema,
            contentPagesWithSchema,
            pagesWithExternalLinks,
            contentPagesWithExtLinks,
            pagesWithOGTags,
            shareablePages,
            securePages,
            pagesWithGoodContent,
            externalCitations,
            avgExternalLinks: contentPages > 0 ? contentPagesWithExtLinks / contentPages : 0,
            topPages: pageScores
        };
    },

    // Generate recommendations based on analysis
    generateRecommendations(analysis) {
        const recommendations = [];
        const total = analysis.totalPages;

        // Author attribution — only flag content pages (articles, blog posts, guides)
        const contentPages = analysis.contentPages;
        const contentPagesWithAuthor = analysis.contentPagesWithAuthor;
        const contentPagesMissingAuthor = contentPages - contentPagesWithAuthor;
        if (contentPages > 0 && contentPagesWithAuthor < contentPages * 0.5) {
            recommendations.push({
                icon: '✍️',
                title: 'Add Author Information to Content Pages',
                description: `${contentPagesMissingAuthor} of your ${contentPages} content pages (blog posts, articles, guides) are missing author information. Add author bylines with credentials to demonstrate expertise. Homepage, contact, and other structural pages are excluded.`,
                priority: contentPagesWithAuthor === 0 ? 'high' : 'medium'
            });
        }

        // Schema markup — flag content pages missing Article/schema, not all pages
        const contentMissingSchema = contentPages - analysis.contentPagesWithSchema;
        if (contentPages > 0 && analysis.contentPagesWithSchema < contentPages * 0.4) {
            recommendations.push({
                icon: '📊',
                title: 'Add Schema Markup to Content Pages',
                description: `${contentMissingSchema} of your ${contentPages} content pages are missing JSON-LD structured data. Add Article, BlogPosting, or NewsArticle schema to help search engines understand your content. Homepage and product pages may use Organization or Product schema separately.`,
                priority: analysis.contentPagesWithSchema === 0 ? 'high' : 'medium'
            });
        }

        // External citations — only meaningful for content pages
        if (contentPages > 0 && analysis.avgExternalLinks < 1.5) {
            recommendations.push({
                icon: '🔗',
                title: 'Add External Citations to Articles',
                description: `Your content pages average ${analysis.avgExternalLinks.toFixed(1)} external links. Link to authoritative sources (studies, official docs, reputable sites) to support your claims. Structural pages like homepage and contact are excluded from this metric.`,
                priority: 'medium'
            });
        }

        // Content depth — only flag content pages, not structural ones
        const contentPagesBelowDepth = contentPages - analysis.pagesWithGoodContent;
        if (contentPages > 0 && analysis.pagesWithGoodContent < contentPages * 0.6) {
            recommendations.push({
                icon: '📝',
                title: 'Improve Content Depth on Articles',
                description: `${contentPagesBelowDepth} of your ${contentPages} content pages have under 300 words. In-depth content demonstrates expertise — aim for 600–1500 words on key articles and guides. Short pages like contact or about are not included in this count.`,
                priority: 'medium'
            });
        }

        // HTTPS
        if (analysis.securePages < total) {
            recommendations.push({
                icon: '🔒',
                title: 'Enable HTTPS Everywhere',
                description: `${total - analysis.securePages} pages are not using HTTPS. Ensure all pages use HTTPS for trust and security.`,
                priority: 'high'
            });
        }

        // If no recommendations, add a positive message
        if (recommendations.length === 0) {
            recommendations.push({
                icon: '🎉',
                title: 'Great E-E-A-T Signals!',
                description: 'Your website demonstrates strong Experience, Expertise, Authoritativeness, and Trust signals. Keep up the good work!',
                priority: 'low'
            });
        }

        return recommendations;
    },

    // Helper: Get score class
    getScoreClass(score) {
        if (score >= 80) return 'score-good';
        if (score >= 60) return 'score-needs-improvement';
        return 'score-poor';
    },

    // Helper: Get score color
    getScoreColor(score) {
        if (score >= 80) return '#10b981';
        if (score >= 60) return '#f59e0b';
        return '#ef4444';
    },

    // Helper: Get percentage
    getPercentage(count, total) {
        return total > 0 ? Math.round((count / total) * 100) : 0;
    }
});

console.log('✅ E-E-A-T Analyzer plugin registered');
