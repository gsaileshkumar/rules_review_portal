# Rukes review portal AI Search POC - Detailed Implementation Plan

## Executive Summary

**Project Goal:** Build a proof-of-concept AI-powered conversational interface for searching and matching User Requests with physical firewall rules using semantic search and vector embeddings.

**Key Innovation:** Replace strict string-based matching with semantic understanding using local AI models and vector databases, reducing false positives and search time from minutes to seconds.

## Problem Statement

### Current System
- **100,000+ user requests** stored in review portal database
- **500,000+ physical firewall rules** implemented on network devices
- Current review system performs **strict comparison** between user requests and physical rules
- Requires **table joins** to generate comparison data
- **High false positive rate** for deficiencies due to format variations
- Engineers spend hours investigating mismatches that are actually semantically equivalent

### Pain Points
1. **Slow Search:** Comparing one user request against 500K rules takes too long
2. **Rigid Matching:** "10.0.0.0/24" vs "10.0.0.1-10.0.0.254" fails despite being equivalent
3. **Manual Investigation:** Engineers manually verify each deficiency
4. **No Context:** System doesn't understand semantic intent behind rules
5. **Poor UX:** No conversational interface for quick lookups


### AI-Powered Semantic Search
Replace exact string matching with semantic understanding using:
- **Vector embeddings** of ELRs and physical rules
- **Similarity search** instead of exact matching
- **Conversational interface** via MCP protocol integration
- **Local AI models** (no external API dependencies)


### Key Capabilities
1. **Bidirectional Search:**
   - "Find physical rules matching reuest_x"
   - "Find ELRs matching physical rule PHYRULE_Y"

2. **Semantic Understanding:**
   - Recognizes equivalent IP ranges in different formats
   - Understands port range variations
   - Identifies semantically similar configurations

3. **Confidence Scoring:**
   - Returns similarity scores (0-100%)
   - Allows threshold-based filtering
   - Explains why matches were found



### Component Breakdown

#### 1. **MCP Client (Claude/Copilot)**
- Existing conversational AI interface
- Users interact naturally: "Find rules for REQ-12345"
- No custom UI development needed

#### 2. **MCP Server (Bridge Layer)**
- Lightweight Python process
- Registers available tools with MCP client
- Forwards users requests to backend API
- Formats responses for conversational display

#### 3. **Backend API Server**
- FastAPI application
- Orchestrates search operations
- Manages embedding pipeline
- Business logic layer

#### 4. **PostgreSQL + pgvector**
- Existing relational data
- Vector columns added to existing tables
- Fast similarity search using ivfflat indexes
- No data migration required