# Execute the released R function and change only the two demonstrated formulas.
# Run: Rscript research/scmultibench-native-r/reproduce.R
args <- commandArgs(trailingOnly = FALSE)
script_arg <- grep('^--file=', args, value = TRUE)
stopifnot(length(script_arg) == 1)
root <- dirname(normalizePath(sub('^--file=', '', script_arg)))
out <- file.path(root, 'results')
dir.create(out, showWarnings = FALSE)
lines <- readLines(file.path(root, 'inputs', 'classification_metrics.Rmd'))
closing <- which(trimws(lines) == '```')[1]
stopifnot(lines[1] == '```{r}', closing > 2)
source_text <- paste(lines[2:(closing - 1)], collapse = '\n')
old_f1 <- 'f1_score <- (2 * (precision * sensitivity) / (precision + sensitivity))'
new_f1 <- 'f1_score <- 2 * diag(cm) / (rowSums(cm) + colSums(cm))'
old_spec <- 'specificity <- diag(prop.table(cm, 2))'
new_spec <- 'specificity <- (sum(cm) - rowSums(cm) - colSums(cm) + diag(cm)) / (sum(cm) - rowSums(cm))'
stopifnot(length(gregexpr(old_f1, source_text, fixed = TRUE)[[1]]) == 1,
          grepl(old_f1, source_text, fixed = TRUE), grepl(old_spec, source_text, fixed = TRUE))
f1_text <- sub(old_f1, new_f1, source_text, fixed = TRUE)
both_text <- sub(old_spec, new_spec, f1_text, fixed = TRUE)
make_function <- function(txt) {
  env <- new.env(parent = globalenv())
  exprs <- parse(text = txt)
  stopifnot(length(exprs) == 1, identical(exprs[[1]][[1]], as.name('<-')),
            identical(exprs[[1]][[2]], as.name('compute_metrics')))
  eval(exprs, envir = env)
  env$compute_metrics
}
functions <- lapply(list(original = source_text, f1_only = f1_text, both_corrected = both_text), make_function)
run_function <- function(fn, truth_file, prediction_file) {
  invisible(capture.output(res <- fn(truth_file, prediction_file)))
  setNames(as.numeric(res[, 1]), rownames(res))
}
# Separate label-level oracle: count each one-vs-rest decision directly.
oracle <- function(truth, prediction) {
  classes <- sort(unique(c(truth, prediction)))
  values <- t(vapply(classes, function(k) {
    tp <- sum(truth == k & prediction == k)
    fp <- sum(truth != k & prediction == k)
    fn <- sum(truth == k & prediction != k)
    tn <- sum(truth != k & prediction != k)
    c(recall = tp / (tp + fn), specificity = tn / (tn + fp), f1 = 2 * tp / (2 * tp + fn + fp))
  }, numeric(3)))
  c('Overall Accuracy' = mean(truth == prediction),
    'Average Accuracy' = mean(values[, 'recall']),
    'specificity' = mean(values[, 'specificity'], na.rm = TRUE),
    'sensitivity' = mean(values[, 'recall'], na.rm = TRUE),
    'f1_score' = mean(values[, 'f1'], na.rm = TRUE))
}
expand_cm <- function(cm) {
  stopifnot(nrow(cm) == ncol(cm), all(cm >= 0), all(rowSums(cm) > 0))
  truth <- prediction <- character()
  for (i in seq_len(nrow(cm))) for (j in seq_len(ncol(cm))) {
    truth <- c(truth, rep(paste0('class_', i), cm[i,j]))
    prediction <- c(prediction, rep(paste0('class_', j), cm[i,j]))
  }
  list(truth = truth, prediction = prediction)
}
evaluate_pair <- function(truth, prediction, name) {
  tf <- tempfile(fileext = '.csv'); pf <- tempfile(fileext = '.csv')
  on.exit(unlink(c(tf, pf)))
  write.csv(data.frame('0' = truth, check.names = FALSE), tf, row.names = FALSE)
  write.csv(data.frame('0' = prediction, check.names = FALSE), pf, row.names = FALSE)
  measured <- lapply(functions, run_function, truth_file = tf, prediction_file = pf)
  expected <- oracle(truth, prediction)
  stopifnot(isTRUE(all.equal(measured$both_corrected, expected, tolerance = 1e-12)))
  stopifnot(isTRUE(all.equal(measured$original[1:4], measured$f1_only[1:4], tolerance = 0)))
  do.call(rbind, lapply(names(measured), function(mode) {
    data.frame(fixture = name, mode = mode, metric = names(measured[[mode]]), value = as.numeric(measured[[mode]]), row.names = NULL)
  }))
}
matrices <- list(
  perfect = diag(c(10, 10, 10)),
  two_failed_classes = matrix(c(10,0,0, 0,0,10, 0,10,0), 3, byrow = TRUE),
  candidate_A = matrix(c(74,1,5, 6,0,9, 0,0,5), 3, byrow = TRUE),
  candidate_B = matrix(c(79,1,0, 4,7,4, 2,1,2), 3, byrow = TRUE),
  all_failed = matrix(c(0,10,0, 0,0,10, 10,0,0), 3, byrow = TRUE),
  one_predicted_class = matrix(c(10,0,0, 10,0,0, 10,0,0), 3, byrow = TRUE)
)
rows <- list()
for (name in names(matrices)) {
  labels <- expand_cm(matrices[[name]])
  rows[[name]] <- evaluate_pair(labels$truth, labels$prediction, name)
}
set.seed(20260907)
for (i in 1:200) {
  cm <- matrix(sample(0:20, 9, replace = TRUE), 3)
  if (i %% 2 == 0) cm[2,2] <- 0
  if (any(rowSums(cm) == 0)) cm <- cm + 1
  labels <- expand_cm(cm)
  rows[[paste0('random_', i)]] <- evaluate_pair(labels$truth, labels$prediction, paste0('random_', i))
}
truth_file <- file.path(root, 'inputs', 'query.csv')
pred_file <- file.path(root, 'inputs', 'predict.csv')
truth <- as.character(read.csv(truth_file)$X0)
prediction <- as.character(read.csv(pred_file)$X0)
stopifnot(length(truth) > 0, length(truth) == length(prediction), !anyNA(truth), !anyNA(prediction))
# Execute the unmodified function directly on the actual release files as well.
demo <- lapply(functions, run_function, truth_file = truth_file, prediction_file = pred_file)
stopifnot(isTRUE(all.equal(demo$both_corrected, oracle(truth, prediction), tolerance = 1e-12)))
rows$released_demo <- do.call(rbind, lapply(names(demo), function(mode) data.frame(
  fixture = 'released_demo', mode = mode, metric = names(demo[[mode]]), value = as.numeric(demo[[mode]]), row.names = NULL)))
results <- do.call(rbind, rows)
write.csv(results, file.path(out, 'metrics.csv'), row.names = FALSE)
cm <- table(truth, prediction)
write.csv(cm, file.path(out, 'demo_confusion_matrix.csv'))
classes <- union(unique(truth), unique(prediction))
per_class <- do.call(rbind, lapply(classes, function(k) {
  tp <- sum(truth == k & prediction == k); fp <- sum(truth != k & prediction == k)
  fn <- sum(truth == k & prediction != k); tn <- sum(truth != k & prediction != k)
  precision <- tp/(tp+fp); recall <- tp/(tp+fn)
  data.frame(class = k, tp=tp, fp=fp, fn=fn, tn=tn,
    old_f1=2*precision*recall/(precision+recall), corrected_f1=2*tp/(2*tp+fp+fn),
    old_specificity=precision, corrected_specificity=tn/(tn+fp))
}))
write.csv(per_class, file.path(out, 'demo_per_class.csv'), row.names=FALSE)
rank_rows <- list()
for (selected_mode in names(functions)) {
  a <- results$value[results$fixture == 'candidate_A' & results$mode == selected_mode]
  b <- results$value[results$fixture == 'candidate_B' & results$mode == selected_mode]
  ranks <- apply(rbind(A=a,B=b), 2, rank, ties.method = 'max')
  mean_ranks <- rowMeans(ranks)
  rank_rows[[selected_mode]] <- data.frame(mode=selected_mode, A=mean_ranks[1], B=mean_ranks[2], row.names=NULL)
}
ranks <- do.call(rbind, rank_rows)
stopifnot(ranks['original','A'] > ranks['original','B'], ranks['f1_only','A'] < ranks['f1_only','B'])
write.csv(ranks, file.path(out, 'synthetic_mean_ranks.csv'), row.names=FALSE)
writeLines(capture.output(sessionInfo()), file.path(out,'sessionInfo.txt'))
cat('Native R original evaluator and isolated formula corrections: PASS\n')
cat('Synthetic fixtures tested:', length(matrices)+200, '\n')
cat('Released demo observations:',length(truth),'classes:',length(classes),'zero-TP classes:',sum(per_class$tp==0),'\n')
print(rows$released_demo, row.names=FALSE)
print(ranks)
cat('This released demo is not identified as an original publication run. No corrected paper leaderboard is claimed.\n')
