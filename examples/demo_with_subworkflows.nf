#!/usr/bin/env nextflow

/*
 * Demo pipeline with subworkflows for testing NF-Subway visualization
 * 
 * This pipeline demonstrates parallel execution paths through subworkflows
 * to create interesting branching patterns in the visualization.
 */

nextflow.enable.dsl=2

params.input = "demo_data/*.txt"
params.outdir = "results"

// ============================================================================
// Preprocessing processes
// ============================================================================

process QUALITY_CHECK {
    publishDir "${params.outdir}/qc", mode: 'copy'
    
    input:
    tuple val(sample_id), path(input_file)
    
    output:
    tuple val(sample_id), path("${sample_id}_qc.txt")
    
    script:
    """
    echo "Quality checking ${sample_id}..." > ${sample_id}_qc.txt
    sleep 2
    echo "Quality check passed!" >> ${sample_id}_qc.txt
    """
}

process TRIM_SEQUENCES {
    publishDir "${params.outdir}/trimmed", mode: 'copy'
    
    input:
    tuple val(sample_id), path(qc_file)
    
    output:
    tuple val(sample_id), path("${sample_id}_trimmed.txt")
    
    script:
    """
    echo "Trimming ${sample_id}..." > ${sample_id}_trimmed.txt
    sleep 2
    echo "Trimming complete!" >> ${sample_id}_trimmed.txt
    """
}

// ============================================================================
// Subworkflow 1: Alignment-based quantification
// ============================================================================

process ALIGN_READS {
    publishDir "${params.outdir}/aligned", mode: 'copy'
    
    input:
    tuple val(sample_id), path(trimmed_file)
    
    output:
    tuple val(sample_id), path("${sample_id}_aligned.txt")
    
    script:
    """
    echo "Aligning ${sample_id}..." > ${sample_id}_aligned.txt
    sleep 3
    echo "Alignment complete!" >> ${sample_id}_aligned.txt
    """
}

process COUNT_FEATURES {
    publishDir "${params.outdir}/counts", mode: 'copy'
    
    input:
    tuple val(sample_id), path(aligned_file)
    
    output:
    tuple val(sample_id), path("${sample_id}_counts.txt")
    
    script:
    """
    echo "Counting features for ${sample_id}..." > ${sample_id}_counts.txt
    sleep 2
    echo "Counting complete!" >> ${sample_id}_counts.txt
    """
}

process NORMALIZE_COUNTS {
    publishDir "${params.outdir}/normalized", mode: 'copy'
    
    input:
    tuple val(sample_id), path(count_file)
    
    output:
    tuple val(sample_id), path("${sample_id}_normalized.txt")
    
    script:
    """
    echo "Normalizing counts for ${sample_id}..." > ${sample_id}_normalized.txt
    sleep 2
    echo "Normalization complete!" >> ${sample_id}_normalized.txt
    """
}

workflow ALIGNMENT_BASED_QUANTIFICATION {
    take:
    trimmed_ch
    
    main:
    aligned = ALIGN_READS(trimmed_ch)
    counts = COUNT_FEATURES(aligned)
    normalized = NORMALIZE_COUNTS(counts)
    
    emit:
    results = normalized
}

// ============================================================================
// Subworkflow 2: Pseudoalignment-based quantification
// ============================================================================

process BUILD_INDEX {
    publishDir "${params.outdir}/salmon_index", mode: 'copy'
    
    input:
    tuple val(sample_id), path(trimmed_file)
    
    output:
    tuple val(sample_id), path("${sample_id}_index.txt")
    
    script:
    """
    echo "Building index for ${sample_id}..." > ${sample_id}_index.txt
    sleep 2
    echo "Index complete!" >> ${sample_id}_index.txt
    """
}

process PSEUDOALIGN_QUANT {
    publishDir "${params.outdir}/salmon_quant", mode: 'copy'
    
    input:
    tuple val(sample_id), path(index_file)
    
    output:
    tuple val(sample_id), path("${sample_id}_quant.txt")
    
    script:
    """
    echo "Quantifying ${sample_id} with Salmon..." > ${sample_id}_quant.txt
    sleep 3
    echo "Quantification complete!" >> ${sample_id}_quant.txt
    """
}

process ADJUST_QUANT {
    publishDir "${params.outdir}/adjusted", mode: 'copy'
    
    input:
    tuple val(sample_id), path(quant_file)
    
    output:
    tuple val(sample_id), path("${sample_id}_adjusted.txt")
    
    script:
    """
    echo "Adjusting quantification for ${sample_id}..." > ${sample_id}_adjusted.txt
    sleep 2
    echo "Adjustment complete!" >> ${sample_id}_adjusted.txt
    """
}

workflow PSEUDOALIGNMENT_QUANTIFICATION {
    take:
    trimmed_ch
    
    main:
    indexed = BUILD_INDEX(trimmed_ch)
    quantified = PSEUDOALIGN_QUANT(indexed)
    adjusted = ADJUST_QUANT(quantified)
    
    emit:
    results = adjusted
}

// ============================================================================
// Subworkflow 3: Assembly-based analysis (third parallel branch)
// ============================================================================

process ASSEMBLE_TRANSCRIPTS {
    publishDir "${params.outdir}/assembly", mode: 'copy'
    
    input:
    tuple val(sample_id), path(trimmed_file)
    
    output:
    tuple val(sample_id), path("${sample_id}_assembly.txt")
    
    script:
    """
    echo "Assembling transcripts for ${sample_id}..." > ${sample_id}_assembly.txt
    sleep 3
    echo "Assembly complete!" >> ${sample_id}_assembly.txt
    """
}

process ANNOTATE_ASSEMBLY {
    publishDir "${params.outdir}/annotation", mode: 'copy'
    
    input:
    tuple val(sample_id), path(assembly_file)
    
    output:
    tuple val(sample_id), path("${sample_id}_annotated.txt")
    
    script:
    """
    echo "Annotating assembly for ${sample_id}..." > ${sample_id}_annotated.txt
    sleep 2
    echo "Annotation complete!" >> ${sample_id}_annotated.txt
    """
}

workflow ASSEMBLY_ANALYSIS {
    take:
    trimmed_ch
    
    main:
    assembled = ASSEMBLE_TRANSCRIPTS(trimmed_ch)
    annotated = ANNOTATE_ASSEMBLY(assembled)
    
    emit:
    results = annotated
}

// ============================================================================
// Final merge and QC processes
// ============================================================================

process MERGE_RESULTS {
    publishDir "${params.outdir}/merged", mode: 'copy'
    
    input:
    path(alignment_files)
    path(pseudo_files)
    path(assembly_files)
    
    output:
    path "merged_results.txt"
    
    script:
    """
    echo "Merging all results..." > merged_results.txt
    echo "Alignment-based: ${alignment_files.size()} samples" >> merged_results.txt
    echo "Pseudoalignment: ${pseudo_files.size()} samples" >> merged_results.txt
    echo "Assembly: ${assembly_files.size()} samples" >> merged_results.txt
    sleep 2
    echo "Merge complete!" >> merged_results.txt
    """
}

process MULTIQC {
    publishDir "${params.outdir}/multiqc", mode: 'copy'
    
    input:
    path(merged_file)
    
    output:
    path "multiqc_report.txt"
    
    script:
    """
    echo "Generating MultiQC report..." > multiqc_report.txt
    cat ${merged_file} >> multiqc_report.txt
    sleep 2
    echo "MultiQC report complete!" >> multiqc_report.txt
    """
}

// ============================================================================
// Main workflow
// ============================================================================

workflow {
    // Create input channel with sample data
    input_ch = channel.of(
        ['sample1', file('demo_data/sample1.txt')],
        ['sample2', file('demo_data/sample2.txt')],
        ['sample3', file('demo_data/sample3.txt')]
    )
    
    // Preprocessing (common path)
    qc_results = QUALITY_CHECK(input_ch)
    trimmed = TRIM_SEQUENCES(qc_results)
    
    // Split into three parallel analysis paths using subworkflows
    alignment_results = ALIGNMENT_BASED_QUANTIFICATION(trimmed)
    pseudo_results = PSEUDOALIGNMENT_QUANTIFICATION(trimmed)
    assembly_results = ASSEMBLY_ANALYSIS(trimmed)
    
    // Collect results from all branches
    all_alignment = alignment_results.results.map { sample_id, result_file -> result_file }.collect()
    all_pseudo = pseudo_results.results.map { sample_id, result_file -> result_file }.collect()
    all_assembly = assembly_results.results.map { sample_id, result_file -> result_file }.collect()
    
    // Merge all results
    merged = MERGE_RESULTS(all_alignment, all_pseudo, all_assembly)
    
    // Generate final report
    MULTIQC(merged)
}

workflow.onComplete {
    println "Pipeline completed at: ${workflow.complete}"
    println "Execution status: ${workflow.success ? 'OK' : 'failed'}"
}
