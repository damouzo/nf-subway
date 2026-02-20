#!/usr/bin/env nextflow

/*
 * Demo pipeline for testing NF-Subway visualization
 * 
 * This pipeline simulates a typical bioinformatics workflow with
 * multiple processes and dependencies.
 */

nextflow.enable.dsl=2

params.input = "demo_data/*.txt"
params.outdir = "results"

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
    sleep 3
    echo "Trimming complete!" >> ${sample_id}_trimmed.txt
    """
}

// Branch 1: Alignment-based analysis
process ALIGN_READS {
    publishDir "${params.outdir}/aligned", mode: 'copy'
    
    input:
    tuple val(sample_id), path(trimmed_file)
    
    output:
    tuple val(sample_id), path("${sample_id}_aligned.txt")
    
    script:
    """
    echo "Aligning ${sample_id}..." > ${sample_id}_aligned.txt
    sleep 4
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

// Branch 2: Quantification-based analysis (parallel to alignment)
process SALMON_INDEX {
    publishDir "${params.outdir}/salmon_index", mode: 'copy'
    
    input:
    tuple val(sample_id), path(trimmed_file)
    
    output:
    tuple val(sample_id), path("${sample_id}_index.txt")
    
    script:
    """
    echo "Building Salmon index for ${sample_id}..." > ${sample_id}_index.txt
    sleep 3
    echo "Index complete!" >> ${sample_id}_index.txt
    """
}

process SALMON_QUANT {
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

// Merge results from both branches
process MULTIQC {
    publishDir "${params.outdir}/multiqc", mode: 'copy'
    
    input:
    path(count_files)
    path(quant_files)
    
    output:
    path "multiqc_report.txt"
    
    script:
    """
    echo "Generating MultiQC report..." > multiqc_report.txt
    echo "Processed counts: ${count_files.size()} samples" >> multiqc_report.txt
    echo "Processed quants: ${quant_files.size()} samples" >> multiqc_report.txt
    sleep 2
    echo "MultiQC report complete!" >> multiqc_report.txt
    """
}

workflow {
    // Create input channel with sample data
    input_ch = channel.of(
        ['sample1', file('demo_data/sample1.txt')],
        ['sample2', file('demo_data/sample2.txt')],
        ['sample3', file('demo_data/sample3.txt')]
    )
    
    // Initial QC and trimming
    qc_results = QUALITY_CHECK(input_ch)
    trimmed = TRIM_SEQUENCES(qc_results)
    
    // Branch 1: Alignment-based quantification
    aligned = ALIGN_READS(trimmed)
    counts = COUNT_FEATURES(aligned)
    
    // Branch 2: Salmon-based quantification (parallel)
    salmon_idx = SALMON_INDEX(trimmed)
    salmon_quant = SALMON_QUANT(salmon_idx)
    
    // Merge both branches into final report
    all_counts = counts.map { sample_id, count_file -> count_file }.collect()
    all_quants = salmon_quant.map { sample_id, quant_file -> quant_file }.collect()
    MULTIQC(all_counts, all_quants)
}

workflow.onComplete {
    println "Pipeline completed at: ${workflow.complete}"
    println "Execution status: ${workflow.success ? 'OK' : 'failed'}"
}
